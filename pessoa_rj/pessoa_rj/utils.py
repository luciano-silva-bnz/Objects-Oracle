from __future__ import annotations

import re
from typing import Iterable, List


def normalize_cpf(value: str | int | float | None) -> str | None:
    if value is None:
        return None
    digits = re.sub(r"\D", "", str(value))
    if not digits:
        return None
    digits = digits.zfill(11)
    return digits if len(digits) == 11 else None


def prepare_cpf_list(text: str) -> list[str]:
    if not text:
        return []
    cleaned = text.replace("\\n", "\n").replace("\\r", "\r")
    cleaned = cleaned.replace("'", "").replace('"', '')
    tokens = re.split(r"[\n\r,;\t]+", cleaned)
    result: list[str] = []
    for token in tokens:
        cpf = normalize_cpf(token)
        if cpf:
            result.append(cpf)
    return [cpf for cpf in result if len(cpf) == 11]
