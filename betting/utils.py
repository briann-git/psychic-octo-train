from datetime import datetime, timezone


def current_season() -> str:
    """Returns the current season string e.g. '2025/26'."""
    now = datetime.now(tz=timezone.utc)
    year = now.year
    if now.month >= 8:
        return f"{year}/{str(year + 1)[-2:]}"
    return f"{year - 1}/{str(year)[-2:]}"
