"""ISO 17442 identifier shape and ISO/IEC 7064 MOD 97-10 checks.

Format/check digits do not establish that an identifier exists in GLEIF.
"""

import re


def lei_checksum_state(value: str) -> str:
    value = value.strip().upper()
    if not value:
        return "empty"
    if len(value) < 20:
        return "incomplete"
    if not re.fullmatch(r"[A-Z0-9]{18}[0-9]{2}", value):
        return "invalid_format"
    digits = "".join(str(int(character, 36)) for character in value)
    return "valid" if int(digits) % 97 == 1 else "invalid_checksum"
