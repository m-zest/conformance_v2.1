"""Synthetic data generators.

The values produced here are structurally valid (checksums pass) so that the
detectors treat them exactly like real data, but they are randomly generated
and do not belong to any person or account. Secret-like values are assembled
at runtime so that no credential-shaped literal is stored in the repository.
"""
from __future__ import annotations

import json
import random
import string
from pathlib import Path

ROSTER_PATH = Path(__file__).with_name("roster.json")

_ODD = {
    **{str(i): v for i, v in enumerate([1, 0, 5, 7, 9, 13, 15, 17, 19, 21])},
    **dict(zip(string.ascii_uppercase,
               [1, 0, 5, 7, 9, 13, 15, 17, 19, 21, 2, 4, 18, 20, 11, 3, 6, 8, 12, 14, 16, 10, 22, 25, 24, 23])),
}
_EVEN = {**{str(i): i for i in range(10)}, **{c: i for i, c in enumerate(string.ascii_uppercase)}}
_MONTHS = "ABCDEHLMPRST"


def load_roster() -> dict:
    data = json.loads(ROSTER_PATH.read_text(encoding="utf-8"))
    for user in data["users"]:
        first, *rest = user["name"].lower().split()
        user["email"] = f"{first}.{''.join(rest)}@{data['domain']}"
        user["id"] = user["email"]
    return data


def luhn_complete(prefix: str, length: int, rng: random.Random) -> str:
    body = prefix + "".join(rng.choice(string.digits) for _ in range(length - len(prefix) - 1))
    total = 0
    for i, ch in enumerate(reversed(body)):
        d = int(ch)
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return body + str((10 - total % 10) % 10)


def card_number(rng: random.Random) -> str:
    prefix, length = rng.choice([("4539", 16), ("4716", 16), ("5425", 16), ("5105", 16), ("3742", 15)])
    digits = luhn_complete(prefix, length, rng)
    if length == 16 and rng.random() < 0.7:
        return " ".join(digits[i:i + 4] for i in range(0, 16, 4))
    return digits


def iban(rng: random.Random) -> str:
    country = rng.choice(["IT", "DE", "FR", "ES", "NL"])
    if country == "IT":
        bban = rng.choice(string.ascii_uppercase) + "".join(rng.choice(string.digits) for _ in range(22))
    elif country == "DE":
        bban = "".join(rng.choice(string.digits) for _ in range(18))
    elif country == "FR":
        bban = "".join(rng.choice(string.digits) for _ in range(23))
    elif country == "ES":
        bban = "".join(rng.choice(string.digits) for _ in range(20))
    else:
        bban = "".join(rng.choice(string.ascii_uppercase) for _ in range(4)) + "".join(
            rng.choice(string.digits) for _ in range(10))
    numeric = "".join(str(int(c, 36)) for c in bban + country + "00")
    check = 98 - int(numeric) % 97
    raw = f"{country}{check:02d}{bban}"
    return " ".join(raw[i:i + 4] for i in range(0, len(raw), 4)) if rng.random() < 0.6 else raw


def codice_fiscale(rng: random.Random) -> str:
    consonants = "BCDFGLMNPRSTVZ"
    body = "".join(rng.choice(consonants) for _ in range(6))
    body += f"{rng.randint(50, 99):02d}{rng.choice(_MONTHS)}{rng.randint(1, 28) + rng.choice([0, 40]):02d}"
    body += rng.choice("ABCDEFGHILM") + f"{rng.randint(1, 999):03d}"
    total = sum(_ODD[c] if i % 2 == 0 else _EVEN[c] for i, c in enumerate(body))
    return body + string.ascii_uppercase[total % 26]


def us_ssn(rng: random.Random) -> str:
    return f"{rng.randint(100, 665):03d}-{rng.randint(10, 99):02d}-{rng.randint(1000, 9999):04d}"


def phone(rng: random.Random) -> str:
    return rng.choice([
        f"+39 3{rng.randint(20, 99)} {rng.randint(100, 999)} {rng.randint(1000, 9999)}",
        f"+49 1{rng.randint(50, 79)} {rng.randint(1000000, 9999999)}",
        f"+44 7{rng.randint(400, 999)} {rng.randint(100000, 999999)}",
    ])


def person(rng: random.Random) -> str:
    first = rng.choice(["Giovanni", "Marta", "Paolo", "Silvia", "Roberto", "Camille", "Jonas", "Helena",
                        "Andrea", "Beatrice", "Victor", "Irene", "Dario", "Katarina", "Felix", "Rosa"])
    last = rng.choice(["Esposito", "Colombo", "Ricci", "Marino", "Schneider", "Lefevre", "Jansen", "Novak",
                       "Costa", "Fontana", "Keller", "Santoro", "Lombardi", "Weber", "Barbieri", "Martin"])
    return f"{first} {last}"


def customer_email(rng: random.Random, name: str | None = None) -> str:
    name = name or person(rng)
    first, last = name.lower().split()[:2]
    return f"{first}.{last}@{rng.choice(['mailbox.example', 'postino.example', 'inbox.example'])}"


def _alnum(rng: random.Random, n: int, alphabet: str = string.ascii_letters + string.digits) -> str:
    return "".join(rng.choice(alphabet) for _ in range(n))


def aws_access_key(rng: random.Random) -> str:
    return "AK" + "IA" + _alnum(rng, 16, string.ascii_uppercase + string.digits)


def aws_secret_key(rng: random.Random) -> str:
    return _alnum(rng, 40, string.ascii_letters + string.digits + "+/")


def github_token(rng: random.Random) -> str:
    return "gh" + "p_" + _alnum(rng, 36)


def api_key(rng: random.Random) -> str:
    return "sk" + "-proj-" + _alnum(rng, 40)


def db_url(rng: random.Random) -> str:
    return ("postgres" + "://billing_app:" + _alnum(rng, 18) +
            f"@db-prod-{rng.randint(1, 4)}.internal.meridian.example:5432/billing")


def private_key_block(rng: random.Random) -> str:
    body = "\n".join(_alnum(rng, 64, string.ascii_letters + string.digits + "+/") for _ in range(4))
    return "-----BEGIN " + "RSA PRIVATE KEY-----\n" + body + "\n-----END " + "RSA PRIVATE KEY-----"


GENERATORS = {
    "card": card_number,
    "iban": iban,
    "cf": codice_fiscale,
    "ssn": us_ssn,
    "phone": phone,
    "name": person,
    "email": customer_email,
    "aws_key": aws_access_key,
    "aws_secret": aws_secret_key,
    "gh_token": github_token,
    "api_key": api_key,
    "db_url": db_url,
    "private_key": private_key_block,
}


def fill(template: str, rng: random.Random) -> str:
    """Replace {placeholders} in a prompt template with freshly generated values."""
    out = template
    for key, gen in GENERATORS.items():
        token = "{" + key + "}"
        while token in out:
            out = out.replace(token, gen(rng), 1)
    return out
