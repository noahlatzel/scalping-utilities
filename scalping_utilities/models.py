from __future__ import annotations

from datetime import datetime, timedelta


def extract_asin(link: str) -> str:
    """Extract an ASIN from a URL or query string containing `asin=`."""
    return link.split("&price")[0].split("asin=")[-1]


class Product:
    """Lightweight product container shared by producer/consumer scripts.

    Note: `ref_price` should be computed by the caller (logic varies between scripts).
    """

    def __init__(
        self,
        name: str,
        shop: str,
        reported_price: float,
        link: str,
        timestamp: datetime,
        ref_price: float,
    ) -> None:
        self.name = name
        self.shop = shop
        self.reported_price = reported_price
        self.link = link
        self.timestamp = timestamp
        self.ref_price = ref_price

        # Derived fields used by Amazon bots
        self.asin = extract_asin(self.link)
        self.default_link = f"https://{self.shop}/dp/{self.asin}"
        self.cart_link = (
            f"https://{self.shop}/gp/aws/cart/add.html?AssociateTag=your-tag-here-20"
            f"&ASIN.1={self.asin}&Quantity.1=2"
        )

        # Search window used by consumers (kept compatible with original behavior)
        search_until = self.timestamp + timedelta(minutes=2)
        self.search_until = search_until.replace(
            year=datetime.today().year, month=datetime.today().month, day=datetime.today().day
        )

