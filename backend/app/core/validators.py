from __future__ import annotations

import re

LOGIN_ID_PATTERN = re.compile(r"^[a-z0-9]+$")
ALLOWED_PASSWORD_SPECIALS = r"!@#$%^&*()\-_=\+\[\]\{\};:,\.\?/\|"
SPECIAL_CHAR_PATTERN = re.compile(rf"[{ALLOWED_PASSWORD_SPECIALS}]")
ALLOWED_PASSWORD_PATTERN = re.compile(rf"^[A-Za-z\d{ALLOWED_PASSWORD_SPECIALS}]+$")
REPEATED_DIGIT_PATTERN = re.compile(r"(\d)\1\1")


def has_sequential_digits(raw: str, min_run: int = 3) -> bool:
    digits = [int(ch) for ch in raw if ch.isdigit()]
    if len(digits) < min_run:
        return False

    ascending_run = 1
    descending_run = 1
    for idx in range(1, len(digits)):
        diff = digits[idx] - digits[idx - 1]
        ascending_run = ascending_run + 1 if diff == 1 else 1
        descending_run = descending_run + 1 if diff == -1 else 1
        if ascending_run >= min_run or descending_run >= min_run:
            return True
    return False


def validate_login_id(value: str) -> str:
    if not LOGIN_ID_PATTERN.fullmatch(value):
        raise ValueError("?꾩씠?붾뒗 ?곷Ц ?뚮Ц?먯? ?レ옄留??ъ슜?????덉뒿?덈떎.")
    return value


def validate_password_rules(value: str) -> str:
    if any(ch.isspace() for ch in value):
        raise ValueError("鍮꾨?踰덊샇?먮뒗 怨듬갚???ъ슜?????놁뒿?덈떎.")
    if not ALLOWED_PASSWORD_PATTERN.fullmatch(value):
        raise ValueError(
            "鍮꾨?踰덊샇 ?뱀닔臾몄옄??! @ # $ % ^ & * ( ) - _ = + [ ] { } ; : , . ? / | 留??ъ슜?????덉뒿?덈떎."
        )

    category_count = sum(
        [
            any(ch.isupper() for ch in value),
            any(ch.islower() for ch in value),
            any(ch.isdigit() for ch in value),
            bool(SPECIAL_CHAR_PATTERN.search(value)),
        ]
    )
    if category_count < 2:
        raise ValueError("鍮꾨?踰덊샇???臾몄옄, ?뚮Ц?? ?レ옄, ?뱀닔臾몄옄 以?2醫낅쪟 ?댁긽???ы븿?댁빞 ?⑸땲??")
    if REPEATED_DIGIT_PATTERN.search(value):
        raise ValueError("鍮꾨?踰덊샇?먮뒗 ?숈씪???レ옄瑜?3?먮━ ?댁긽 ?곗냽?쇰줈 ?ъ슜?????놁뒿?덈떎.")
    if has_sequential_digits(value):
        raise ValueError("鍮꾨?踰덊샇?먮뒗 ?곗냽???レ옄瑜?3?먮━ ?댁긽 ?ъ슜?????놁뒿?덈떎.")
    return value
