import random
import os
from pathlib import Path
import requests
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import pickle

from dotenv import load_dotenv
from .models import Product


bought = False
loop = asyncio.get_event_loop()
post_soups = []

# Load environment and derive paths/credentials
load_dotenv()
REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCT_DATA_PATH = Path(
    os.getenv("PRODUCT_DATA_PATH", str(REPO_ROOT / "artifacts" / "product_data.pkl"))
)
USERNAME = os.getenv("AMAZON_USERNAME", "")
USERNAME_1 = os.getenv("AMAZON_USERNAME_ALT", "")
PASSWORD = os.getenv("AMAZON_PASSWORD", "")
PASSWORD_1 = os.getenv("AMAZON_PASSWORD_ALT", "")

merchantID_default = "A3JWKAKR8XB7XF"
merchantID_warehouse = "A2L77EE7U53NWQ"
merchantID_global = "A3OJWAJQNSBARP"

buy_now_form = {
    "offerListingID": "4HPGX6NpRaNP3jcq%2FEwaSPShbF2YDDr0iG3ONiCr%2FWG7BJleqBbMFsdsSkPQpVOKrXp4ABSOjTbNDOqKHEXvq5YNFDZ2K%2FyLTUo80jJJSea6ypVnTV61HflZ%2BnUwowbEbiL7rqUj0dexw4MvrGT%2FJu1cZ%2BkKXif95haXEi7ybHDiU76t2Act4g%3D%3D",
    "usePrimeHandler": "0",
    "submit.buy-now": "",
}

impfung_form = {
    "worker_id": "0",
    "appointment_ids": "16660",
    "store_id": "9107",
    "date": "2021-06-08",
    "is_internal": "false",
}

buy_now_form_backup = {
    "ASIN": "B089ZSQF1L",
    "ctaDeviceType": "desktop",
    "ctaPageType": "detail",
    "isAddon": "0",
    "isMerchantExclusive": "0",
    "itemCount": "1",
    "merchantID": "A3JWKAKR8XB7XF",
    "nodeID": "",
    "qid": "",
    "rebateId": "",
    "sellingCustomerID": "",
    "sourceCustomerOrgListID": "",
    "sourceCustomerOrgListItemID": "",
    "sr": "",
    "storeID": "",
    "submit.add-to-registry.wishlist": "Auf die Liste",
    "tagActionCode": "",
    "usePrimeHandler": "0",
    "viewID": "glance",
    "wlPopCommand": "",
    "submit.buy-now": "Test",
}

# define URL where login form is located
site = "https://www.amazon.de/gp/sign-in.html"

# initiate session
session = requests.Session()

# define session headers
session.headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/44.0.2403.62 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": site,
}

login_pages = [
    "https://www.amazon.de/",
    "https://www.amazon.fr/",
    "https://www.amazon.it/",
    "https://www.amazon.es/",
    "https://www.amazon.co.uk/",
]


def login_internal(temp_username, temp_password, page):
    resp = session.get(page + "gp/sign-in.html")
    html = resp.text

    # get BeautifulSoup object of the html of the login page
    soup = BeautifulSoup(html, "lxml")
    # scrape login page to get all the needed inputs required for login
    data = {}
    form = soup.find("form", {"name": "signIn"})
    for field in form.find_all("input"):
        try:
            data[field["name"]] = field["value"]
        except KeyError:
            pass
    # add username and password to the data for post request
    data["email"] = temp_username
    data["password"] = temp_password

    # submit post request with username / password and other needed info
    post_resp = session.post(page + "ap/signin", data=data)

    post_soup = BeautifulSoup(post_resp.content, "lxml")
    proof = post_soup.find_all("title")[0].text
    if (
        "Konto" in proof
        or "compte" in proof
        or "account" in proof
        or "cuenta" in proof
        or "Account" in proof
    ):
        status("INFO: Login Successful.")
    else:
        status("ERROR: Login Failed (LOGIN_FAIL).")
        status(proof)
    # Now logged in and can proceed


def login(account):
    if account == "alt":
        temp_username = USERNAME_1
        temp_password = PASSWORD_1
    else:
        temp_username = USERNAME
        temp_password = PASSWORD
    # Logging into multiple Amazon locales
    for page in login_pages:
        loop.run_in_executor(None, login_internal, temp_username, temp_password, page)


def process_buy_now_form(data):
    data["submit.buy-now"] = "Senden"
    data["itemCount"] = "1"
    for k in [
        "gift-wrap",
        "asin.1",
        "quantity.1",
        "offeringID.1",
        "asin.2",
        "quantity.2",
        "offeringID.2",
        "submit.add-to-cart",
        "CSRF",
        "",
    ]:
        try:
            data.pop(k)
        except KeyError:
            pass


def process_checkout_form(data):
    for k in [
        "",
        "countdownId",
        "countdownThreshold",
        "fasttrackExpiration",
        "showSimplifiedCountdown",
        "promiseAsin-0",
        "promiseTime-0",
        "afn-gift-wrap",
    ]:
        try:
            data.pop(k)
        except KeyError:
            pass
    data["javaEnabled"] = "false"
    data["language"] = "de-DE"
    data["needsThirdPartyRedirect"] = "1"
    data["paymentDisplayName"] = "Visa / Electron"
    data["placeYourOrder1"] = "1"
    data["timeZone"] = "-120"
    data["screenColorDepth"] = "24"
    data["screenHeight"] = "1440"
    data["screenWidth"] = "2560"
    data["gift-message-text"] = ""
    data["forceshipsplitpreference0.0"] = ""
    data["isQuantityInvariant"] = ""
    data["hasWorkingJavascript"] = "1"
    data["isfirsttimecustomer"] = "0"
    data["isTFXEligible"] = ""
    data["isFxEnabled"] = ""


def process_page(raw_page):
    if ".de" in raw_page:
        return "amazon.de"
    if ".it" in raw_page:
        return "amazon.it"
    if ".fr" in raw_page:
        return "amazon.fr"
    if ".es" in raw_page:
        return "amazon.es"
    if ".co.uk" in raw_page:
        return "amazon.co.uk"
    return "amazon.de"


def post_buy_now_form_internal(page, product):
    global post_soups
    page = process_page(page)
    post_resp = session.post(
        "https://www."
        + str(page)
        + "/gp/product/handle-buy-box/ref=dp_start-bbf_1_glance",
        data=buy_now_form,
    )
    post_soup = BeautifulSoup(post_resp.content, "lxml")
    title = post_soup.find_all("title")[0].text
    if (
        "Bezahlvorgang" in title
        or "Processus" in title
        or "Preparando" in title
        or "Preparing" in title
        or "preparazione" in title
    ):
        status("INFO: Succesfully loaded checkout-page.")
        post_soups.append(post_soup)
    else:
        error = post_soup.find(id="sc-important-message-alert")
        if error is not None:
            time.sleep(random.uniform(1, 2))


def post_buy_now_form(product: Product):
    global post_soups
    post_soups = []
    for page in login_pages:
        loop.run_in_executor(None, post_buy_now_form_internal, page, product)


def post_checkout_form(product: Product, soup):
    global bought
    data = {}
    page = process_page(soup.find_all("title")[0].text)
    form = soup.find("form", {"id": "spc-form"})
    if form is None:
        status("ERROR: Item can't be shipped to selected address.")
        bought = True
        return
    for field in form.find_all("input"):
        try:
            data[field["name"]] = field["value"]
        except KeyError:
            pass
    process_checkout_form(data)
    if float(data.get("purchaseTotal", "0")) < product.ref_price:
        initiator = (
            "https://www."
            + page
            + "/gp/buy/spc/handlers/static-submit-decoupled.html/ref"
            "=ox_spc_place_order?ie=UTF8&hasWorkingJavascript="
        )
        post_resp = session.post(initiator, data=data)
        post_soup = BeautifulSoup(post_resp.content, "lxml")
        if "  " in post_soup.find_all("title")[0].text:
            status("INFO: Checkout Successful")
            bought = True
        else:
            status("ERROR: Could not checkout (PAYMENT_ERROR).")
            status("DEBUG: " + post_soup.find_all("title")[0].text)
            return
    else:
        status(
            "ERROR: Price is too high. ("
            + data.get("purchaseTotal", "0")
            + "). (MAX_PRICE_EXCEEDED)."
        )


def buy_now(product: Product):
    global bought
    bought = False
    while product.search_until > datetime.today():
        # Has to be logged into amazon. Opens product page and submits buy-now form.
        post_buy_now_form(product)
        # Now on checkout-page. Last step is submitting the final-checkout form.
        for soup in post_soups:
            print(soup)
        quit()
        for post_soup in post_soups:
            loop.run_in_executor(None, post_checkout_form, product, post_soup)
        if bought is True:
            status("INFO: Succesfully bought " + product.name + " .")
            break
        time.sleep(random.uniform(1.5, 2.5))
    else:
        status("ERROR: Could not buy product (MAX_TIME_EXCEEDED).")


def post_checkout(form_data):
    initiator = (
        "https://www.amazon.de/gp/buy/spc/handlers/static-submit-decoupled.html/ref=ox_spc_place_order?"
        "ie=UTF8&hasWorkingJavascript="
    )
    post_resp = session.post(initiator, data=form_data)
    post_soup = BeautifulSoup(post_resp.content, "lxml")
    text_file = open("page.html", "w")
    text_file.write(post_soup.prettify())
    text_file.close()
    if "Bezahlvorgang" in post_soup.find_all("title")[0].text:
        status("Checkout Successful")
    else:
        status("Checkout Failed")
        status(post_soup.find_all("title")[0].text)


def status(string):
    print("[" + str(datetime.today().time()) + "] " + string)


def retrieve_product() -> Product | None:
    product = None
    with open(PRODUCT_DATA_PATH, "rb") as product_file:
        while product is None:
            try:
                product = pickle.load(product_file)
            except EOFError:
                time.sleep(0.01)
                pass
    return product


def main(account):
    login(account)
    while not bought:
        recent_product = retrieve_product()
        if (
            recent_product is not None
            and recent_product.search_until >= datetime.today()
        ):
            status("INFO: Found: " + recent_product.name)
            status(
                "INFO: Reported price: "
                + str(recent_product.reported_price)
                + " €"
            )
            status("INFO: Reference price: " + str(recent_product.ref_price) + " €")
            status("INFO: Product link: " + recent_product.default_link)
            status("INFO: Attempting buy")
            buy_now(recent_product)
            if bought:
                status("SUCCESS: " + recent_product.name)
                status("SUCCESS: " + str(recent_product.reported_price))
                status("SUCCESS: " + recent_product.shop)
                status("INFO: Finishing up.")
                time.sleep(120)


# dummy = Product("DUMMY", "Amazon.de", 1300, "B016XJG65Y", datetime.today(), 0)
# login("1")
# time.sleep(3)
# buy_now(dummy)
main("1")

