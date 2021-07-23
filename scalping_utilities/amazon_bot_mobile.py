from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
)
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.ui import Select
from datetime import datetime, timedelta
import time
import pickle
import os
from pathlib import Path
from dotenv import load_dotenv
from amazoncaptcha import AmazonCaptcha

"""Initializing variables"""
load_dotenv()
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHROMEDRIVER = REPO_ROOT / "chromedriver.exe"
CHROMEDRIVER_PATH = Path(os.getenv("CHROMEDRIVER_PATH", str(DEFAULT_CHROMEDRIVER)))
PRODUCT_DATA_PATH = Path(
    os.getenv("PRODUCT_DATA_PATH", str(REPO_ROOT / "artifacts" / "product_data.pkl"))
)
options = webdriver.ChromeOptions()
prefs = {"profile.managed_default_content_settings.images": 2}
options.add_experimental_option("prefs", prefs)
options.add_argument(
    "--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 10_3 like Mac OS X) "
    "AppleWebKit/602.1.50 (K"
    "HTML, like Gecko) CriOS/56.0.2924.75 Mobile/14E5239e Safari/602.1"
)
# options.add_argument("--headless")
caps = DesiredCapabilities().CHROME
caps["pageLoadStrategy"] = "none"
driver = webdriver.Chrome(str(CHROMEDRIVER_PATH), options=options, desired_capabilities=caps)
email = os.getenv("AMAZON_USERNAME", "")
password = os.getenv("AMAZON_PASSWORD", "")
shops = [
    "www.amazon.de",
    "www.amazon.fr",
    "www.amazon.es",
    "www.amazon.it",
    "www.amazon.co.uk",
]
ps5 = "https://discord.com/channels/768363408109469697/802674800786145311"
rtx3060 = "https://discord.com/channels/768363408109469697/806954441056059422"
rtx3060ti = "https://discord.com/channels/768363408109469697/802674527850725377"
rtx3070 = "https://discord.com/channels/768363408109469697/802674552541806662"
rtx3080 = "https://discord.com/channels/768363408109469697/802674584473567303"
rtx3090 = "https://discord.com/channels/768363408109469697/802674601519611925"
bought = False
availability_keywords = [
    "nicht verfügbar",
    "Actuellement indisponible",
    "Non disponibile",
    "No disponible",
    "unavailable",
]





def construct_merchant_link(product):
    merchant = ""
    if "de" in product.shop:
        merchant = "A3JWKAKR8XB7XF"
    if "es" in product.shop:
        merchant = "A1AT7YVPFBWXBL"
    if "fr" in product.shop:
        merchant = "A1X6FK5RDHNB96"
    if "it" in product.shop:
        merchant = "A11IL2PNWYJU7H"
    if "uk" in product.shop:
        merchant = "A3P5ROKL5A1OLE"
    link = (
        "https://"
        + product.shop
        + "/dp/"
        + product.asin
        + "/ref=sr_1_1?__mk_de_DE=ÅMÅŽÕÑ&m="
        + merchant
    )
    return link


def retrieve_product():
    product = None
    with open(PRODUCT_DATA_PATH, "rb") as product_file:
        while product is None:
            try:
                product = pickle.load(product_file)
            except EOFError:
                time.sleep(0.01)
                pass
    return product


def captcha_check():
    try:
        captcha_input = driver.find_element_by_id("captchacharacters")
        status("ALERT: Captcha found.")
        src = driver.find_element_by_css_selector("img[src^='https']")
        captcha = AmazonCaptcha(src)
        solved_captcha = captcha.solve()
        captcha_input.send_keys(solved_captcha)
        captcha_input.submit()
    except NoSuchElementException:
        pass


def buy_now_and_other_sellers():
    captcha_check()
    timer = datetime.today() + timedelta(seconds=1.5)
    temp = [False, False, False]  # [buy_now, other_sellers, add_cart]
    while timer > datetime.today():
        captcha_check()
        try:
            availability = driver.find_element_by_id("availability").get_property(
                "innerText"
            )
            for word in availability_keywords:
                if word in availability:
                    status("INFO: No stock/not available.")
                    return temp
        except NoSuchElementException:
            pass
        except StaleElementReferenceException:
            pass
        try:
            driver.find_element_by_id("buy-now-button")
            status("INFO: Buy-now button found.")
            temp[0] = True
            return temp
        except NoSuchElementException:
            pass
        try:
            driver.find_element_by_id("add-to-cart-button-ubb-mobile")
            status("INFO: Add-to-basket found.")
            temp[2] = True
            try:
                driver.find_element_by_id("buy-now-button")
                status("INFO: Buy-now button found.")
                temp[0] = True
            except NoSuchElementException:
                pass
            return temp
        except NoSuchElementException:
            pass
        try:
            button = driver.find_element_by_css_selector(
                "span[data-action^='show-all-offers-display']"
            )
            button.find_element_by_css_selector("a[role^='button']")
            status("INFO: Other-sellers found.")
            temp[1] = True
            return temp
        except NoSuchElementException:
            pass
    if temp[0] is False:
        status("ERROR: Could not find buy-now button.")
    if temp[1] is False:
        status("ERROR: Could not find other-sellers button.")
    if temp[2] is False:
        status("ERROR: Could not find add-to-basket button.")
    return temp


def buy_now_internal():
    driver.find_element_by_id("buy-now-button").click()


def checkout():
    timer = datetime.today() + timedelta(seconds=5)
    while timer > datetime.today():
        try:
            driver.find_element_by_id("prime-interstitial-nothanks-button").click()
            status("INFO: Prime offer skipped.")
        except NoSuchElementException:
            try:
                driver.find_element_by_name("placeYourOrder1")
                status("INFO: Ready to check out.")
                return True
            except NoSuchElementException:
                pass
    status("ERROR: Could not check out.")
    return False


def checkout_internal():
    try:
        driver.find_element_by_name("placeYourOrder1").click()
        status("DEBUG: Checkout with .click()")
        status("INFO: Checkout succesful.")
    except NoSuchElementException:
        driver.find_element_by_name("placeYourOrder1").submit()
        status("DEBUG: Checkout with .submit()")
        status("INFO: Checkout succesful.")


def other_sellers_loaded():
    timer = datetime.today() + timedelta(seconds=2)
    while timer > datetime.today():
        try:
            driver.find_element_by_xpath("/html/body/div[1]/div[2]/div/div[1]/span/h1")
            return True
        except NoSuchElementException:
            pass
    return False


def other_sellers_internal():
    try:
        driver.find_element_by_id("inline-twister-expander-content-style_name")
        driver.implicitly_wait(0.3)
        button = driver.find_element_by_css_selector(
            "span[data-action^='show-all-offers-display']"
        )
        button.find_element_by_css_selector("a[role^='button']").click()
    except NoSuchElementException:
        try:
            button = driver.find_element_by_css_selector(
                "span[data-action^='show-all-offers-display']"
            )
            button.find_element_by_css_selector("a[role^='button']").click()
        except NoSuchElementException:
            return other_sellers_internal()
        except ElementClickInterceptedException:
            return other_sellers_internal()


def get_best_other_sellers_offer(product):
    while not other_sellers_loaded():
        pass
    try:
        offer_list = driver.find_elements_by_id("aod-offer")
        for offer in offer_list:
            raw_price = offer.find_element_by_css_selector(
                "span[class^='a-offscreen']"
            ).get_property("outerText")
            price = clean_price(raw_price)
            if price < product.ref_price:
                offer.find_element_by_name("submit.addToCart").click()
                status("INFO: Added third-party-offer to cart.")
                return True
        status("ERROR: Actual price is higher than maximum price.")
    except NoSuchElementException:
        status("ERROR: No offers found.")
        pass
    except IndexError:
        status("ERROR: No offers found.")
        pass
    return False


def clean_price(price):
    if "€" in price:
        return float(
            price.replace(".", "")
            .replace(" ", "")
            .replace(",", ".")
            .replace("€", "")
            .replace("\xa0", "")
        )
    if "£" in price:
        return (
            float(
                price.replace(",", "")
                .replace(" ", "")
                .replace("£", "")
                .replace(",", "")
                .replace("\xa0", "")
            )
            * 1.19
        )


def cart_to_checkout():
    timer = datetime.today() + timedelta(seconds=1)
    while timer > datetime.today():
        try:
            driver.find_element_by_name("proceedToRetailCheckout")
            status("INFO: Proceeding to checkout.")
            return True
        except NoSuchElementException:
            pass
    status("ERROR: Shopping cart is empty.")
    return False


def cart_to_checkout_internal():
    driver.find_element_by_name("proceedToRetailCheckout").click()


def add_to_basket_internal():
    try:
        driver.find_element_by_id("add-to-cart-button-ubb-mobile").click()
        status("INFO: Added product to basket.")
        status("DEBUG: add-to-basket clicked.")
    except NoSuchElementException:
        driver.find_element_by_id("add-to-cart-button-ubb-mobile").submit()
        status("INFO: Added product to basket.")
        status("DEBUG: add-to-basket submitted.")


def buy_product(product):
    driver.get(construct_merchant_link(product))
    if product.search_until > datetime.today() and not bought:
        ops = buy_now_and_other_sellers()
        if ops[0]:
            if product.reported_price < 600:
                set_quantity(2)
            buy_now_internal()
            if checkout():
                checkout_internal()
                bank_loaded()
            else:
                driver.get(product.default_link)
                return buy_product(product)
        else:
            if ops[1]:
                other_sellers_internal()
                added = get_best_other_sellers_offer(product)
                if added and cart_to_checkout():
                    cart_to_checkout_internal()
                    if checkout():
                        checkout_internal()
                        bank_loaded()
                    else:
                        driver.get(product.default_link)
                        return buy_product(product)
                else:
                    status("INFO: Reloading")
                    return buy_product(product)
            else:
                if ops[2]:
                    add_to_basket_internal()
                    if cart_to_checkout():
                        cart_to_checkout_internal()
                        if checkout():
                            checkout_internal()
                            bank_loaded()
                        else:
                            driver.get(product.default_link)
                            return buy_product(product)
                else:
                    status("INFO: Reloading.")
                    return buy_product(product)
    else:
        status("INFO: Could not buy product (time limit exceeded // no stock).")


def init_amazon():
    status("INFO: Starting Amazon Login.")
    counter = 0
    for shop in shops:
        error = True
        while error:
            driver.get("https://" + shop)
            captcha_check()
            loaded = False
            while not loaded:
                try:
                    driver.find_element_by_id("nav-logobar-greeting").click()
                    loaded = True
                except NoSuchElementException:
                    pass
                except StaleElementReferenceException:
                    pass
            loaded = False
            send_cred = False
            while not loaded:
                try:
                    if not send_cred:
                        driver.find_element_by_id("ap_email_login").send_keys(email)
                        send_cred = True
                    driver.find_element_by_xpath(
                        "/html/body/div[1]/div[2]/div[3]/div[2]/div/"
                        "div[2]/div/div[2]/form/div[3]/div/span/span/input"
                    ).submit()
                    loaded = True
                except NoSuchElementException:
                    pass
                except StaleElementReferenceException:
                    pass
            loaded = False
            send_cred = False
            timer = datetime.today() + timedelta(seconds=2)
            while not loaded:
                if timer > datetime.today():
                    try:
                        driver.find_element_by_css_selector(
                            "input[name^='rememberMe']"
                        ).submit()
                        if not send_cred:
                            driver.find_element_by_id("ap_password").send_keys(password)
                            driver.find_element_by_id("signInSubmit").submit()
                            send_cred = True
                        loaded = True
                    except NoSuchElementException:
                        pass
                    except StaleElementReferenceException:
                        pass
                else:
                    error = True
                    loaded = True
            loaded = False
            timer = datetime.today() + timedelta(seconds=2)
            while not loaded:
                if timer > datetime.today():
                    try:
                        if "Noah" in driver.find_element_by_id(
                            "nav-greeting-name"
                        ).get_property("innerText"):
                            loaded = True
                            error = False
                            counter += 1
                    except NoSuchElementException:
                        pass
                    except StaleElementReferenceException:
                        pass
                else:
                    # status("DEBUG: Set error to True because parsing took too long.")
                    error = True
                    loaded = True

    if counter == 5:
        status("INFO: Amazon Login succesful.")
    else:
        status("ERROR: Wrong password/email.")


def main():
    init_amazon()
    while not bought:
        recent_product = retrieve_product()
        if (
            recent_product is not None
            and recent_product.search_until >= datetime.today()
        ):
            buy_product(recent_product)
            if bought:
                status("SUCCESS: " + recent_product.name)
                status("SUCCESS: " + recent_product.reported_price)
                status("SUCCESS: " + recent_product.shop)
                status("INFO: Finishing up.")
                time.sleep(120)


def status(string):
    print("[" + str(datetime.today().time()) + "] " + string)


def set_quantity(number):
    try:
        quantity = Select(driver.find_element_by_id("mobileQuantityDropDown"))
        quantity.select_by_value(str(number))
        status("INFO: Set the quantity to " + str(number) + ".")
    except NoSuchElementException:
        status("ERROR: Could not set quantity to the requested number.")


def bank_loaded():
    global bought
    timer = datetime.today() + timedelta(seconds=4)
    while timer > datetime.today():
        try:
            driver.find_element_by_css_selector("span[class^='a-size-medium']")
            status("INFO: Banking loaded. Authorize payment through banking app.")
            bought = True
            return
        except NoSuchElementException:
            pass
    status("ERROR: Could not load banking.")


if __name__ == "__main__":
    main()
