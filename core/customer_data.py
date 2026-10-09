import re


def normalize_phone(value):
    """Canonical Brazilian phone for grouping contacts, never authentication."""
    digits = re.sub(r'\D', '', value or '')
    if len(digits) in (10, 11):
        digits = '55' + digits
    return digits
