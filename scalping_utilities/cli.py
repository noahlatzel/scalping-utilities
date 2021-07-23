from __future__ import annotations

from pathlib import Path
import argparse

from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn


import re
import pickle
import plotly.graph_objects as go

from scalping_utilities.ebay import extract_raw_data, per_day_list_alt, smooth_list, median, get_ebay_list


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Plotly chart generation for eBay sold listings."
    )
    parser.add_argument("product", help="Search term, e.g., 'RX 6700 XT'")
    parser.add_argument(
        "--condition", type=int, default=3, help="eBay condition code (default: 3)"
    )
    parser.add_argument(
        "--mode",
        default="ALL",
        help="eBay LH_* mode flag, e.g., BIN or ALL (default: ALL)",
    )
    parser.add_argument(
        "--artifacts", default="artifacts", help="Directory to store output artifacts"
    )
    args = parser.parse_args()

    load_dotenv()  # load PLOTLY_* etc.
    console = Console()

    artifacts_dir = Path(args.artifacts)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    with Progress(
        SpinnerColumn(), TextColumn("[bold blue]{task.description}"), console=console
    ) as progress:
        t_fetch = progress.add_task("Fetching eBay data…", start=True)
        products = get_ebay_list(args.product, args.condition, args.mode, 1, 200, 1)
        progress.update(t_fetch, completed=1)

        if len(products) < 10:
            console.print("[red]ERROR:[/red] Could not retrieve enough data from eBay")
            return

        t_smooth = progress.add_task("Smoothing and aggregating…", start=True)
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
        progress.update(t_smooth, completed=1)

        t_render = progress.add_task("Rendering Plotly chart…", start=True)
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=x_raw, y=y_raw, mode="markers", marker=dict(size=4), name=args.product
            )
        )
        fig.add_trace(
            go.Scatter(
                x=x_avg, y=y_median, line=dict(width=2, color="red"), name="Median"
            )
        )
        fig.add_trace(
            go.Scatter(
                x=x_avg, y=y_avg, line=dict(width=2, color="green"), name="Average"
            )
        )
        fig.add_trace(
            go.Scatter(
                x=x_avg,
                y=y1_number,
                line=dict(width=2, color="blue"),
                name="Number Sold",
            )
        )

        slug = (
            re.sub(r"[^a-zA-Z0-9_-]+", "-", args.product.strip()).strip("-").lower()
            or "plot"
        )
        html_path = artifacts_dir / f"{slug}.html"
        fig.write_html(str(html_path), auto_open=False)
        progress.update(t_render, completed=1)

        t_save = progress.add_task("Saving raw data…", start=True)
        raw_path = artifacts_dir / f"{slug}_raw.pkl"
        with raw_path.open("wb") as fh:
            pickle.dump(products, fh)
        progress.update(t_save, completed=1)

    console.print(f"✅ Done. Saved chart to `{html_path}` and raw data alongside.")


if __name__ == "__main__":  # pragma: no cover
    main()
