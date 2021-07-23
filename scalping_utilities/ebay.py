from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

import os
import pickle
import re

import requests
from bs4 import BeautifulSoup


# HTTP session with basic headers
_session = requests.Session()
_session.headers = {
    "User-Agent": os.getenv(
        "REQUESTS_USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ),
    "referer": "https://www.ebay.de/",
}


@dataclass(order=True)
class Product:
    price: float
    date: datetime


def _round_cent(euro: float) -> float:
    return int(euro * 100) / 100


def average(products: List[Product]) -> float:
    if not products:
        return 0.0
    return _round_cent(sum(p.price for p in products) / len(products))


def median(products: List[Product]) -> List:
    if not products:
        return [0, 0, 0, 0, 0, datetime.today(), 0]
    products_sorted = sorted(products)
    n = len(products_sorted)
    if n <= 3:
        top25 = _round_cent(products_sorted[n // 2].price)
        top75 = _round_cent(products_sorted[n // 2].price)
    else:
        top25 = _round_cent(products_sorted[(n * 3) // 4].price)
        top75 = _round_cent(products_sorted[n // 4].price)
    top50 = _round_cent(products_sorted[n // 2].price)
    minimum = _round_cent(products_sorted[0].price)
    maximum = _round_cent(products_sorted[-1].price)
    timestamp = products_sorted[0].date
    avg = average(products_sorted)
    return [top50, top25, top75, minimum, maximum, timestamp, avg]


def process_price(raw: str) -> float:
    print(raw)
    # normalize spaces and separators
    s = raw.replace("\xa0", " ").strip()
    s = s.replace("EUR", "")
    # handle ranges like "100 bis 120" or "100 to 120"
    m = re.split(r"\s*(bis|to)\s*", s)
    if len(m) >= 3:
        left = _parse_price(m[0])
        right = _parse_price(m[-1])
        return (left + right) / 2
    return _parse_price(s)


def _parse_price(s: str) -> float:
    return float(s.replace(" EUR", "").replace(".", "").replace(",", "."))


def process_date_alt(text: str) -> Optional[datetime]:
    repl = {
        "Jan": "01",
        "Feb": "02",
        "Mrz": "03",
        "Apr": "04",
        "Mai": "05",
        "Jun": "06",
        "Jul": "07",
        "Aug": "08",
        "Sep": "09",
        "Okt": "10",
        "Nov": "11",
        "Dez": "12",
    }
    z = text.replace(".", "").replace("Verkauft", "").strip()
    for k, v in repl.items():
        z = z.replace(k, v)
    try:
        return datetime.strptime(z, "%d %m %Y")
    except ValueError:
        return None


def remove_list(a: List[Product], b: List[Product]) -> List[Product]:
    out = list(a)
    for item in b:
        if item in out:
            out.remove(item)
    return out


def per_day_list_alt(products: List[Product]) -> List[List[Product]]:
    data: List[List[Product]] = []
    temp = products.copy()
    if not temp:
        return []
    reference_date = temp[0].date
    group: List[Product] = [p for p in temp if p.date == reference_date]
    temp = remove_list(temp, group)
    return [group] + per_day_list_alt(temp)


def smooth_list(products: List[Product]) -> None:
    avg = average(products)
    removed = 0
    # Remove outliers based on the original heuristic (66% .. 140%)
    for p in list(products):
        if p.price < avg * 0.66 or p.price > avg * 1.4:
            products.remove(p)
            removed += 1
    if removed:
        smooth_list(products)


def extract_raw_data(products: List[Product]) -> Tuple[List[datetime], List[float]]:
    x, y = [], []
    for p in products:
        x.append(p.date)
        y.append(p.price)
    return x, y


def get_ebay_list(
    product: str,
    condition: int,
    mode: str,
    locationcode: int,
    size: int,
    page: int,
) -> List[Product]:
    search = product.replace(" ", "+")
    url = (
        "https://www.ebay.de/sch/i.html?_from=R40"
        f"&_nkw={search}"
        "&_sacat=0"
        f"&LH_ItemCondition={condition}"
        f"&LH_{mode}=1"
        "&LH_Sold=1"
        "&LH_Complete=1"
        "&rt=nc"
        f"&LH_PrefLoc={locationcode}"
        f"&_ipg={size}"
        f"&_pgn={page}"
    )
    r = _session.get(url)
    soup = BeautifulSoup(r.text, "lxml")

    # Try to handle captcha page form post (best-effort, may be skipped)
    try:
        captcha_form = soup.find("form", attrs={"id": "captcha_form"})
        if captcha_form is not None:
            data = {}
            for f in captcha_form.find_all("input"):
                name = f.get("name")
                if name:
                    data[name] = f.get("value", "")
            r = _session.post("https://www.ebay.de/splashui/captcha_submit", data=data)
            soup = BeautifulSoup(r.text, "lxml")
    except Exception:
        pass

    listings = soup.select('li[class*="s-item"]')
    pages = soup.find_all("ol", attrs={"class": "pagination__items"})
    pages = BeautifulSoup(str(pages), "lxml").find_all("li")
    pages = BeautifulSoup(str(pages), "lxml").text.strip("][").split(", ")

    try:
        soup.find("div", attrs={"class": "srp-save-null-search__title"}).find(
            "h3", attrs={"class": "srp-save-null-search__heading"}
        )
        return []
    except Exception:
        pass

    try:
        error_field = soup.find(
            "div", attrs={"class": "srp-river-answer srp-river-answer--REWRITE_START"}
        )
        error_field = error_field.find_previous_sibling()["data-view"]
    except Exception:
        error_field = "Not Found"

    if not len(pages) == 1:
        if page > 10000 / size or (
            pages and pages[-1].isdigit() and int(pages[-1]) < page
        ):
            return []
    else:
        if page == 2:
            return []

    results: List[Product] = []
    for listing in listings:
        if error_field in str(listing):
            break
        price_tag = listing.find("span", attrs={"class": "s-item__price"})
        date_tag = listing.find(
            "span", attrs={"class": "s-item__ended-date s-item__endedDate"}
        )
        price_text = BeautifulSoup(str(price_tag), "lxml").text
        date_text = BeautifulSoup(str(date_tag), "lxml").text

        # Try to reconstruct date when split into multiple spans
        year_span = listing.find("span", attrs={"class": "POSITIVE"})
        year_spans = BeautifulSoup(str(year_span), "lxml").find_all("span")
        for year_prob in year_spans:
            dotfinder = BeautifulSoup(str(year_prob), "lxml").text
            if "." in dotfinder:
                cls = BeautifulSoup(str(year_prob), "lxml").span.get("class")
                if cls:
                    year_prob2 = BeautifulSoup(str(year_span), "lxml").find_all(
                        "span", attrs={"class": cls}
                    )
                    joined = (
                        BeautifulSoup(str(year_prob2), "lxml")
                        .text.strip("][")
                        .split(", ")
                    )
                    date_text = "".join(joined)

        if "None" not in price_text and "None" not in date_text:
            price_val = process_price(price_text)
            date_val = process_date_alt(date_text)
            if date_val is None:
                # retry page to normalize inconsistent date strings
                return get_ebay_list(product, condition, mode, locationcode, size, page)
            results.append(Product(price=price_val, date=date_val))

    if not results:
        return []
    if results[-1].date > datetime.today() - timedelta(days=180):
        return results + get_ebay_list(
            product, condition, mode, locationcode, size, page + 1
        )
    return results


def run_plotly_pipeline(
    product: str, condition: int, mode: str, artifacts: Path
) -> Path:
    # Core pipeline used by CLI
    products = get_ebay_list(product, condition, mode, 1, 200, 1)
    if len(products) < 10:
        raise RuntimeError("Could not retrieve enough data from eBay")

    # Store raw data
    artifacts.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", product.strip()).strip("-").lower() or "plot"
    raw_path = artifacts / f"{slug}_raw.pkl"
    with raw_path.open("wb") as fh:
        pickle.dump(products, fh)

    # Smooth and aggregate
    smooth_list(products)
    day_lists = per_day_list_alt(products)
    y1_number = [len(day) for day in day_lists]
    averages = [median(day) for day in day_lists]

    x_raw, y_raw = extract_raw_data(products)
    x_avg, y_median, y_avg = [], [], []
    for av in averages:
        if av != 0:
            x_avg.append(av[5])
            y_median.append(av[0])
            y_avg.append(av[6])

    # Generate HTML plotly chart (no auto-open) and store in artifacts
    try:
        import plotly.graph_objects as go
    except Exception as e:
        raise RuntimeError(f"Plotly is required to render charts: {e}")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=x_raw, y=y_raw, mode="markers", marker=dict(size=4), name=product)
    )
    fig.add_trace(
        go.Scatter(x=x_avg, y=y_median, line=dict(width=2, color="red"), name="Median")
    )
    fig.add_trace(
        go.Scatter(x=x_avg, y=y_avg, line=dict(width=2, color="green"), name="Average")
    )
    fig.add_trace(
        go.Scatter(
            x=x_avg, y=y1_number, line=dict(width=2, color="blue"), name="Number Sold"
        )
    )

    html_path = artifacts / f"{slug}.html"
    fig.write_html(str(html_path), auto_open=False)

    # Optional Chart Studio credentials from environment
    username = os.getenv("PLOTLY_USERNAME")
    api_key = os.getenv("PLOTLY_API_KEY")
    if username and api_key:
        try:
            import chart_studio

            chart_studio.tools.set_credentials_file(username=username, api_key=api_key)
        except Exception:
            # Credentials provided but chart_studio missing or failed; continue silently
            pass

    return html_path
