# DEPRECATED
Unfortunately, the scraping discord server is not working anymore and anti-botting measures have increased. 
The following code is old and will probably not work anymore.

Scalping Utilities
===================

Tools for scraping and reacting to product availability/pricing.

What’s included
---------------
- eBay CLI: Fetches recent sold listings and renders an interactive Plotly chart.
- Discord scraper: Watches selected Discord channels and forwards Amazon offers.
- Amazon bots: Experimental scripts to navigate Amazon flows after a forwarded offer.

Quick Start
-----------
- Create/activate a Python 3.12 environment (conda/venv).
- Install in editable mode: `pip install -e .`
- Copy `.env.example` to `.env` and fill in credentials as needed.

eBay CLI
--------
- Run: `run_plotly "RX 6700 XT" --condition 3 --mode ALL`
- Outputs an HTML chart under `./artifacts/<slug>.html`.

Discord + Amazon Flow
---------------------
- Set credentials in `.env` (see “Environment Variables”).
- Ensure ChromeDriver is available and set `CHROMEDRIVER_PATH` if the default (`./chromedriver.exe`) is not correct.
- The Discord scraper writes a `Product` object to `PRODUCT_DATA_PATH` (default `./artifacts/product_data.pkl`),
  which the Amazon scripts read.
- Run Discord scraper (example): `python scalping_utilities/discord_bot.py`
- Run Amazon bots (examples):
  - Form flow: `python scalping_utilities/amazon_bot_form.py`
  - Mobile flow: `python scalping_utilities/amazon_bot_mobile.py`

Environment Variables
---------------------
- PLOTLY_USERNAME: Optional Plotly username for the eBay CLI.
- PLOTLY_API_KEY: Optional Plotly API key for the eBay CLI.
- AMAZON_USERNAME: Amazon login email used by Amazon scripts.
- AMAZON_PASSWORD: Amazon login password used by Amazon scripts.
- AMAZON_USERNAME_ALT: Optional alternate Amazon login email.
- AMAZON_PASSWORD_ALT: Optional alternate Amazon login password.
- DISCORD_EMAIL: Discord login email for the scraper.
- DISCORD_PASSWORD: Discord login password for the scraper.
- CHROMEDRIVER_PATH: Path to ChromeDriver binary. Default `./chromedriver.exe`.
- PRODUCT_DATA_PATH: Path to the product pickle. Default `./artifacts/product_data.pkl`.
