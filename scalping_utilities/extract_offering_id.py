from datetime import datetime, timedelta
import time
import pickle
from bs4 import BeautifulSoup
import requests
from pathlib import Path
import os
from dotenv import load_dotenv

from .models import Product


load_dotenv()
REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCT_DATA_PATH = Path(
    os.getenv("PRODUCT_DATA_PATH", str(REPO_ROOT / "artifacts" / "product_data.pkl"))
)

session = requests.Session()
session.headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/44.0.2403.62 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}
merchant_ids = ['A3JWKAKR8XB7XF', 'A1AT7YVPFBWXBL', 'A11IL2PNWYJU7H', 'A1X6FK5RDHNB96', 'A3P5ROKL5A1OLE']


class OfferListing:
    def __init__(self, name, shop, offerlistingid, asin, merchantid):
        self.name = name
        self.shop = shop
        self.offerlistingid = offerlistingid
        self.asin = asin
        self.merchantid = merchantid


def retrieve_product() -> Product:
    product = None
    with open(PRODUCT_DATA_PATH, 'rb') as product_file:
        while product is None:
            try:
                product = pickle.load(product_file)
            except EOFError:
                time.sleep(0.01)
                pass
    return product


def open_amazon_from_link_and_extract(product: Product):
    # Now on partalert.net
    response = session.get(product.link)
    html = response.text
    soup = BeautifulSoup(html, 'lxml')

    # Extracting link to amazon
    href_amazon = soup.find('a', {'id': 'href'}).get('href')

    # Extract relevant information, ASIN, OfferListingID, merchantID
    while product.search_until < datetime.today():
        data = extract_data_from_amazon(href_amazon)
        offer = OfferListing(product.name, product.shop, data['offerListingID'], data['ASIN'], data['merchantID'])
        for merchant_id in merchant_ids:
            if data['merchantID'] == merchant_id:
                save_offerlistingid(offer)
                return
            else:
                status("DEBUG: Could not find proper offerListingID.")
                pass
    status("ERROR: Could not find proper offerListingID.")


def extract_data_from_amazon(link):
    # Now on amazon
    response = session.get(link)
    html = response.text
    soup = BeautifulSoup(html, 'lxml')

    # Extracting addToCart form data
    atc_form = soup.find('form', {'id': 'addToCart'})
    data = {}
    for field in atc_form.find_all('input'):
        try:
            data[field['id']] = field['value']
        except KeyError:
            pass
    return data


def status(string):
    print("[" + str(datetime.today().time()) + "] " + string)


def construct_offer_string(offer: OfferListing):
    offer_string = offer.name + "," + offer.shop + "," + offer.offerlistingid + "," \
                   + offer.merchantid + "," + offer.asin
    return offer_string


def save_offerlistingid(offer: OfferListing):
    offer_string = construct_offer_string(offer)
    with open("offerListingIDs.txt", "w") as text_file:
        print(offer_string, file=text_file)


status("INFO: Starting extractor.")
while True:
    pot_product = retrieve_product()
    while pot_product.search_until < datetime.today():
        pass
    else:
        status("INFO: Found alert.")
        open_amazon_from_link_and_extract(pot_product)

