from datetime import datetime, timedelta
from pathlib import Path
import os
import pickle

from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
)
from selenium.webdriver.common.keys import Keys

from .models import Product


# Load environment variables from local .env if present
load_dotenv()

# Relative defaults with env overrides
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHROMEDRIVER = REPO_ROOT / "chromedriver.exe"
CHROMEDRIVER_PATH = Path(os.getenv("CHROMEDRIVER_PATH", str(DEFAULT_CHROMEDRIVER)))
PRODUCT_DATA_PATH = Path(
    os.getenv("PRODUCT_DATA_PATH", str(REPO_ROOT / "artifacts" / "product_data.pkl"))
)

options = webdriver.ChromeOptions()
options.page_load_strategy = "none"
# options.add_argument("--headless")
options.add_argument("--mute-audio")
driver_discord = webdriver.Chrome(str(CHROMEDRIVER_PATH), options=options)

# Discord credentials
email_discord = os.getenv("DISCORD_EMAIL", "")
password_discord = os.getenv("DISCORD_PASSWORD", "")

search_until = datetime.today()
bought = False

ps5 = "https://discord.com/channels/768363408109469697/802674800786145311"
rtx3060 = "https://discord.com/channels/768363408109469697/806954441056059422"
rtx3060ti = "https://discord.com/channels/768363408109469697/802674527850725377"
rtx3070 = "https://discord.com/channels/768363408109469697/802674552541806662"
rtx3080 = "https://discord.com/channels/768363408109469697/802674584473567303"
rtx3090 = "https://discord.com/channels/768363408109469697/802674601519611925"
base_link = "https://discord.com/channels/768363408109469697/779062266262716426"


def set_refprice(name: str) -> float:
    ref_price = 1000
    if "3060" in name:
        ref_price = 550
    if "Ti" in name or "ti" in name:
        ref_price = 650
    if "3070" in name:
        ref_price = 900
    if "3080" in name:
        ref_price = 1350
    if "3090" in name:
        ref_price = 2300
    if "PS" in name or "tation" in name and "5" in name:
        ref_price = 520
    return ref_price


def init_discord(link: str) -> None:
    status("INFO: Starting Discord Login.")
    driver_discord.get(link)
    loaded = False
    while not loaded:
        try:
            driver_discord.find_element_by_name("email").send_keys(email_discord)
            driver_discord.find_element_by_name("password").send_keys(
                password_discord, Keys.ENTER
            )
            loaded = True
        except NoSuchElementException:
            pass
    timer = datetime.today() + timedelta(seconds=20)
    while timer > datetime.today():
        try:
            driver_discord.find_element_by_css_selector("div[class^='nameTag']")
            status("INFO: Discord Login succesful.")
            return
        except NoSuchElementException:
            pass
        except StaleElementReferenceException:
            pass
    status("ERROR: Wrong password/email.")


def process_discord_price(price: str) -> float:
    price = price.split("at")[0].replace(" ", "")
    if "€" in price:
        return float(price.replace(",", "").replace("€", ""))
    if "£" in price:
        return float(price.replace(",", "").replace("£", "")) * 1.19
    return 0.0


def extract_offer_data(offer):
    try:
        name = offer.find_element_by_css_selector(
            "div[class^='embedTitle']"
        ).get_property("innerText")
        shop = offer.find_element_by_css_selector(
            "div[class^='embedAuthor']"
        ).get_property("innerText")
        if "mazon" in shop:
            data_field = offer.find_elements_by_css_selector(
                "div[class^='embedField-']"
            )
            price = (
                data_field[0]
                .find_element_by_css_selector("div[class^='embedFieldValue']")
                .get_property("innerText")
            )
            price = process_discord_price(price)
            link = (
                data_field[2]
                .find_element_by_css_selector("div[class^='embedFieldValue']")
                .get_property("innerText")
            )
            timestamp = offer.find_element_by_css_selector(
                "span[class^='latin12Compact']"
            ).get_property("textContent")
            timestamp = datetime.strptime(timestamp, "[%H:%M] ")
            ref_price = set_refprice(name)
            return Product(name, shop, price, link, timestamp, ref_price)
    except StaleElementReferenceException:
        status("ERROR: Couldn't extract offer data.")
        extract_offer_data(offer)


def get_offers():
    timer = datetime.today() + timedelta(seconds=20)
    while timer > datetime.today():
        try:
            driver_discord.find_element_by_css_selector("div[class^='nameTag']")
            break
        except NoSuchElementException:
            pass
        except StaleElementReferenceException:
            pass
    offers = []
    raw_offers = driver_discord.find_elements_by_css_selector("div[class^='message']")
    for offer in raw_offers:
        try:
            offer.find_element_by_css_selector("div[class^='embedAuthor']")
            offers.append(offer)
        except NoSuchElementException:
            pass
        except StaleElementReferenceException:
            pass
    return offers


def get_channels():
    channels = []
    try:
        raw_channels = driver_discord.find_elements_by_css_selector(
            "div[class^='containerDefault--']"
        )
        for channel in raw_channels:
            channel_name = channel.find_element_by_css_selector(
                "div[class^='channelName']"
            ).get_property("textContent")
            if (
                "rtx" in channel_name
                or "ps5" in channel_name
                or "test" in channel_name
                or "allgemein" in channel_name
            ):
                channels.append(channel)
    except NoSuchElementException:
        status("ERROR: Could not find channels.")
        get_channels()
    return channels


def wait_for_mention(channels):
    found = False
    while not found:
        for channel in channels:
            try:
                channel.find_element_by_css_selector("div[class^='mentionsBadge']")
                status("INFO: Found mention!")
                found = True
                channel.click()
            except NoSuchElementException:
                pass
            except StaleElementReferenceException:
                pass
            except ElementClickInterceptedException:  # WORKAROUND
                status("ERROR: ElementClickInterceptedException")
        recent_offers = get_offers()
        if len(recent_offers) > 0:
            recent_offer = extract_offer_data(recent_offers[-1])
            if recent_offer is not None:
                difference = datetime.today() - recent_offer.timestamp
                if (
                    difference.seconds < 65
                    and recent_offer.reported_price < recent_offer.ref_price
                ):
                    return


def status(string: str) -> None:
    print("[" + str(datetime.today().time()) + "] " + string)


def forward_product(product: Product) -> None:
    PRODUCT_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PRODUCT_DATA_PATH, "wb") as output:
        output.truncate(0)
        pickle.dump(product, output, pickle.HIGHEST_PROTOCOL)


def starter_msg(link: str) -> None:
    if link == rtx3060:
        status("INFO: Searching for RTX 3060.")
    if link == rtx3060ti:
        status("INFO: Searching for RTX 3060 Ti.")
    if link == rtx3070:
        status("INFO: Searching for RTX 3070.")
    if link == rtx3080:
        status("INFO: Searching for RTX 3080.")
    if link == rtx3090:
        status("INFO: Searching for RTX 3090.")
    if link == ps5:
        status("INFO: Searching for PlayStation 5.")


def main(link: str) -> None:
    starter_msg(link)
    init_discord(link)
    while True:
        recent_offers = get_offers()
        if len(recent_offers) > 0:
            recent_offer = extract_offer_data(recent_offers[-1])
            if recent_offer is not None:
                difference = datetime.today() - recent_offer.timestamp
                if (
                    difference.seconds < 65
                    and recent_offer.reported_price < recent_offer.ref_price
                ):
                    status("INFO: Found: " + recent_offer.name)
                    status(
                        "INFO: Reported price: "
                        + str(recent_offer.reported_price)
                        + " €"
                    )
                    forward_product(recent_offer)
                    difference = datetime.today() - recent_offer.timestamp
                    while difference.seconds < 65:
                        difference = datetime.today() - recent_offer.timestamp


def process_offers() -> None:
    recent_offers = get_offers()
    if len(recent_offers) > 0:
        recent_offer = extract_offer_data(recent_offers[-1])
        if recent_offer is not None:
            difference = datetime.today() - recent_offer.timestamp
            if (
                difference.seconds < 65 * 60 * 6
                and recent_offer.reported_price < recent_offer.ref_price
            ):
                status("INFO: Found: " + recent_offer.name)
                status(
                    "INFO: Reported price: "
                    + str(recent_offer.reported_price)
                    + " €"
                )
                forward_product(recent_offer)
                difference = datetime.today() - recent_offer.timestamp
                while difference.seconds < 65:
                    difference = datetime.today() - recent_offer.timestamp


def main_all() -> None:
    init_discord(rtx3080)
    channel_list = get_channels()
    while True:
        wait_for_mention(channel_list)
        recent_offers = get_offers()
        if len(recent_offers) > 0:
            recent_offer = extract_offer_data(recent_offers[-1])
            if recent_offer is not None:
                difference = datetime.today() - recent_offer.timestamp
                if (
                    difference.seconds < 65
                    and recent_offer.reported_price < recent_offer.ref_price
                ):
                    status("INFO: Found: " + recent_offer.name)
                    status(
                        "INFO: Reported price: "
                        + str(recent_offer.reported_price)
                        + " €"
                    )
                    forward_product(recent_offer)
                    difference = datetime.today() - recent_offer.timestamp
                    while difference.seconds < 65:
                        difference = datetime.today() - recent_offer.timestamp


def new_main() -> None:
    init_discord("https://discord.com/channels/768363408109469697/802674384120446996")
    channel_list = get_channels()
    channel_links = []
    for channel in channel_list:
        link = channel.find_element_by_css_selector("a[href^='/channels']").get_property(
            "href"
        )
        channel_links.append(link)
        driver_discord.execute_script("window.open()")
    driver_discord.close()
    i = 0
    for window in driver_discord.window_handles:
        driver_discord.switch_to.window(window)
        driver_discord.get(channel_links[i])
        i += 1
    handles = driver_discord.window_handles
    while True:
        for window in handles:
            driver_discord.switch_to.window(window)
            process_offers()


new_main()

