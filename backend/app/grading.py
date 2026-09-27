"""Проверка ответов, которые ребёнок вводит сам.

Сравниваем «по смыслу», а не посимвольно: регистр, лишние пробелы, ё/е, точка в конце
и вид апострофа не должны отнимать звезду. Для математики числа можно сравнивать по значению.
"""

import re
from fractions import Fraction

_SPACES = re.compile(r"\s+")
_TRAILING_PUNCT = re.compile(r"[.!?;]+$")
_NUMBER = re.compile(r"^[+-]?(\d+([.,]\d*)?|[.,]\d+)$")
_FRACTION = re.compile(r"^[+-]?\d+\s*/\s*\d+$")
_APOSTROPHES = str.maketrans({"’": "'", "‘": "'", "`": "'", "ʼ": "'"})


def normalize(text: str) -> str:
    s = str(text or "").translate(_APOSTROPHES).lower().replace("ё", "е")
    s = _SPACES.sub(" ", s).strip()
    return _TRAILING_PUNCT.sub("", s).strip()


def as_number(text: str) -> Fraction | None:
    """'0,5', '.5', '1/2', '-3' → Fraction; всё остальное → None."""
    s = normalize(text).replace(" ", "")
    try:
        if _NUMBER.match(s):
            return Fraction(s.replace(",", "."))
        if _FRACTION.match(s):
            num, den = s.split("/")
            return Fraction(int(num), int(den)) if int(den) else None
    except (ValueError, ZeroDivisionError):
        return None
    return None


def is_text_answer_correct(given: str | None, accepted: list[str], numeric: bool) -> bool:
    if given is None or not normalize(given):
        return False
    g = normalize(given)
    if any(g == normalize(a) for a in accepted):
        return True
    if numeric:
        g_num = as_number(given)
        return g_num is not None and any(as_number(a) == g_num for a in accepted)
    return False
