"""Finnish reference data for the synthetic generator.

Merchant chains are public brand names used only as payee labels; people are
random first/last-name combinations; IBANs are format-valid (mod-97) but use
the synthetic bank code ``799`` so they are not meant to resolve to a real
account (see regulatory-context.md §4: synthetic data only).
"""

import random
from dataclasses import dataclass

from petosvahti.domain import Channel

CITIES = (
    "Helsinki",
    "Espoo",
    "Tampere",
    "Vantaa",
    "Oulu",
    "Turku",
    "Jyväskylä",
    "Lahti",
    "Kuopio",
)

FIRST_NAMES = (
    "Aino", "Anna", "Antti", "Eero", "Elina", "Emilia", "Heidi", "Jussi", "Juha", "Kaisa",
    "Laura", "Matti", "Mikko", "Noora", "Olli", "Pekka", "Sanna", "Timo", "Ville", "Johanna",
)  # fmt: skip

LAST_NAMES = (
    "Virtanen", "Korhonen", "Mäkinen", "Nieminen", "Mäkelä", "Hämäläinen", "Laine",
    "Heikkinen", "Koskinen", "Järvinen", "Lehtonen", "Saarinen", "Salminen", "Heinonen",
    "Niemi", "Kinnunen", "Salonen", "Turunen", "Lindholm", "Rantanen",
)  # fmt: skip


@dataclass(frozen=True, slots=True)
class MerchantChain:
    """A merchant brand with its typical ticket size (median EUR) and rail."""

    name: str
    median_eur: float
    channel: Channel
    local: bool = True  # has a branch per city ("Prisma Turku") vs one online entity


EVERYDAY_CHAINS = (
    MerchantChain("K-Citymarket", 45.0, Channel.CARD),
    MerchantChain("S-Market", 28.0, Channel.CARD),
    MerchantChain("Prisma", 52.0, Channel.CARD),
    MerchantChain("Lidl", 31.0, Channel.CARD),
    MerchantChain("K-Market", 14.0, Channel.CARD),
    MerchantChain("Alepa", 12.0, Channel.CARD),
    MerchantChain("R-kioski", 6.0, Channel.CARD),
    MerchantChain("Neste", 48.0, Channel.CARD),
    MerchantChain("ABC", 39.0, Channel.CARD),
    MerchantChain("Hesburger", 11.0, Channel.CARD),
    MerchantChain("Fazer Café", 9.0, Channel.CARD),
    MerchantChain("Robert's Coffee", 7.0, Channel.CARD),
    MerchantChain("Alko", 26.0, Channel.CARD),
    MerchantChain("Yliopiston Apteekki", 18.0, Channel.CARD),
    MerchantChain("Tokmanni", 24.0, Channel.CARD),
    MerchantChain("Stockmann", 65.0, Channel.CARD),
    MerchantChain("Clas Ohlson", 29.0, Channel.CARD),
    MerchantChain("HSL", 3.2, Channel.CARD, local=False),
    MerchantChain("VR", 34.0, Channel.ONLINE_BANK, local=False),
    MerchantChain("Wolt", 24.0, Channel.CARD, local=False),
    MerchantChain("Foodora", 22.0, Channel.CARD, local=False),
    MerchantChain("Verkkokauppa.com", 70.0, Channel.ONLINE_BANK, local=False),
    MerchantChain("Zalando", 55.0, Channel.ONLINE_BANK, local=False),
    MerchantChain("Elisa", 35.0, Channel.ONLINE_BANK, local=False),
    MerchantChain("Helen", 62.0, Channel.ONLINE_BANK, local=False),
)

BIG_TICKET_CHAINS = (
    MerchantChain("Gigantti", 650.0, Channel.CARD),
    MerchantChain("Power", 520.0, Channel.ONLINE_BANK, local=False),
    MerchantChain("IKEA", 480.0, Channel.CARD),
    MerchantChain("Asko", 900.0, Channel.ONLINE_BANK, local=False),
)

# Legit travel destinations: (country, merchant names seen there).
TRAVEL = (
    ("SE", ("ICA Stockholm", "Pressbyrån Arlanda", "SL Stockholm")),
    ("EE", ("Rimi Tallinn", "Viru Keskus", "Bolt Tallinn")),
    ("ES", ("Mercadona Málaga", "Renfe", "Café Central Málaga")),
    ("DE", ("Rewe Berlin", "Deutsche Bahn", "Späti Kreuzberg")),
)

# Countries a hijacked session or card-testing script is seen from.
FRAUD_COUNTRIES = ("NL", "GB", "US", "LT", "RO", "DE")


def person_name(rng: random.Random) -> str:
    return f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"


def synthetic_iban(rng: random.Random) -> str:
    """A format-valid Finnish IBAN (FIkk + 14 digits) on synthetic bank code 799."""
    bban = "799" + "".join(str(rng.randrange(10)) for _ in range(11))
    # ISO 13616: move "FI00" to the end, map letters (F=15, I=18), mod 97.
    check = 98 - int(bban + "151800") % 97
    return f"FI{check:02d}{bban}"


def iban_is_valid(iban: str) -> bool:
    if len(iban) < 5 or not iban[:2].isalpha() or not iban[2:].isdigit():
        return False
    rearranged = iban[4:] + iban[:4]
    digits = "".join(str(int(ch, 36)) for ch in rearranged)
    return int(digits) % 97 == 1


def slug(text: str) -> str:
    return "".join(ch if ch.isalnum() else "-" for ch in text.lower()).strip("-")
