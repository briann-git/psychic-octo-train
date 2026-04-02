from datetime import datetime, timezone


def season_from_date(dt: datetime) -> str:
    """
    Derives season string from a datetime.
    August onwards = new season (e.g. 2025/26).
    Before August = season started previous year (e.g. 2025/26 for April 2026).
    """
    year = dt.year
    if dt.month >= 8:
        return f"{year}/{str(year + 1)[-2:]}"
    return f"{year - 1}/{str(year)[-2:]}"


def current_season() -> str:
    """Returns the current season string."""
    return season_from_date(datetime.now(tz=timezone.utc))
