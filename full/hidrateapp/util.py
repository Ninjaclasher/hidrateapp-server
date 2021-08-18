def sanitize_isodate(isodate):
    if isodate.endswith('Z'):
        return isodate[:-1] + '+00:00'
    return isodate


def unsanitize_isodate(isodate):
    if isodate.endswith('+00:00'):
        return isodate[:-6] + 'Z'
    return isodate


def parse_int_safe(value):
    MAX_DIGITS = 10000
    if isinstance(value, str) and len(value) > MAX_DIGITS:
        raise ValueError()
    return int(value)
