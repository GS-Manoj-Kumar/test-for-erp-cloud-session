"""GST helpers. Pure Python: no Frappe imports, so they run under plain pytest."""

import re

# GST state codes (as used in the first two digits of a GSTIN).
STATE_CODES = {
    "01": "Jammu and Kashmir",
    "02": "Himachal Pradesh",
    "03": "Punjab",
    "04": "Chandigarh",
    "05": "Uttarakhand",
    "06": "Haryana",
    "07": "Delhi",
    "08": "Rajasthan",
    "09": "Uttar Pradesh",
    "10": "Bihar",
    "11": "Sikkim",
    "12": "Arunachal Pradesh",
    "13": "Nagaland",
    "14": "Manipur",
    "15": "Mizoram",
    "16": "Tripura",
    "17": "Meghalaya",
    "18": "Assam",
    "19": "West Bengal",
    "20": "Jharkhand",
    "21": "Odisha",
    "22": "Chhattisgarh",
    "23": "Madhya Pradesh",
    "24": "Gujarat",
    "26": "Dadra and Nagar Haveli and Daman and Diu",
    "27": "Maharashtra",
    "29": "Karnataka",
    "30": "Goa",
    "31": "Lakshadweep",
    "32": "Kerala",
    "33": "Tamil Nadu",
    "34": "Puducherry",
    "35": "Andaman and Nicobar Islands",
    "36": "Telangana",
    "37": "Andhra Pradesh",
    "38": "Ladakh",
}

STATES = sorted(STATE_CODES.values())

_GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def normalize_gstin(value):
    return (value or "").strip().upper()


def gstin_checksum(first14):
    """Check character for the first 14 chars of a GSTIN (base-36 Luhn variant)."""
    total = 0
    for i, ch in enumerate(first14):
        product = _CHARS.index(ch) * (2 if i % 2 else 1)
        total += product // 36 + product % 36
    return _CHARS[(36 - total % 36) % 36]


def gstin_error(value):
    """Return an error message for an invalid GSTIN, or None if it is valid."""
    g = normalize_gstin(value)
    if len(g) != 15:
        return f"GSTIN must be 15 characters (got {len(g)})."
    if not _GSTIN_RE.match(g):
        return "GSTIN format is invalid (expected e.g. 27AAPFU0939F1ZV)."
    if g[:2] not in STATE_CODES:
        return f"GSTIN state code {g[:2]} is not a known Indian state code."
    if gstin_checksum(g[:14]) != g[14]:
        return "GSTIN check digit does not match."
    return None


def state_from_gstin(value):
    g = normalize_gstin(value)
    return STATE_CODES.get(g[:2]) if len(g) >= 2 else None
