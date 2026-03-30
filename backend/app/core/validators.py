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
        raise ValueError("아이디는 영문 소문자와 숫자만 사용할 수 있습니다.")
    return value


def validate_password_rules(value: str) -> str:
    if any(ch.isspace() for ch in value):
        raise ValueError("비밀번호에는 공백을 사용할 수 없습니다.")
    if not ALLOWED_PASSWORD_PATTERN.fullmatch(value):
        raise ValueError(
            "비밀번호 특수문자는 ! @ # $ % ^ & * ( ) - _ = + [ ] { } ; : , . ? / | 만 사용할 수 있습니다."
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
        raise ValueError("비밀번호는 대문자, 소문자, 숫자, 특수문자 중 2종류 이상을 포함해야 합니다.")
    if REPEATED_DIGIT_PATTERN.search(value):
        raise ValueError("비밀번호에는 동일한 숫자 3자리를 연속으로 사용할 수 없습니다.")
    if has_sequential_digits(value):
        raise ValueError("비밀번호에는 연속된 숫자 3자리 이상을 사용할 수 없습니다.")
    return value
