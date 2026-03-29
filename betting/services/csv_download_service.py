import logging
import os
import tempfile
import time
from pathlib import Path

import httpx

from betting.adapters.football_data import LEAGUE_CODES

logger = logging.getLogger(__name__)


class CsvDownloadService:
    def __init__(
        self,
        cache_dir: str,
        max_age_hours: int = 24,
    ) -> None:
        self._cache_dir = cache_dir
        self._max_age_hours = max_age_hours
        Path(cache_dir).mkdir(parents=True, exist_ok=True)

    def get(self, league: str, season: str) -> str:
        """
        Returns the local file path to the CSV for the given league and season.
        Downloads if not cached or if cache is stale.
        Raises on download failure with no cached fallback available.
        If a stale cached file exists and download fails, logs a warning
        and returns the stale file rather than raising.
        """
        dest = self._cache_path(league, season)

        if not self._is_stale(dest):
            logger.info("Cache hit for %s %s: %s", league, season, dest)
            return str(dest)

        logger.info("Downloading CSV for %s %s to %s", league, season, dest)
        try:
            self._download(league, season, dest)
            return str(dest)
        except Exception as exc:
            if dest.exists():
                logger.warning(
                    "Download failed for %s %s (%s), returning stale cache %s",
                    league, season, exc, dest,
                )
                return str(dest)
            logger.error(
                "Download failed for %s %s and no cache available: %s",
                league, season, exc,
            )
            raise

    def _cache_path(self, league: str, season: str) -> Path:
        """
        Returns deterministic cache path.
        Example: {cache_dir}/PL_2526.csv
        """
        season_code = self._season_code(season)
        return Path(self._cache_dir) / f"{league}_{season_code}.csv"

    def _is_stale(self, path: Path) -> bool:
        """True if file does not exist or mtime is older than max_age_hours."""
        if not path.exists():
            return True
        age_seconds = time.time() - path.stat().st_mtime
        return age_seconds > self._max_age_hours * 3600

    def _download(self, league: str, season: str, dest: Path) -> None:
        """
        Downloads CSV to dest. Uses httpx with timeout=15.
        Derives URL from LEAGUE_CODES and season string.
        Raises ValueError if league not in LEAGUE_CODES.
        Raises httpx.HTTPError on network failure.
        """
        if league not in LEAGUE_CODES:
            raise ValueError(f"League {league!r} not in LEAGUE_CODES")

        league_code = LEAGUE_CODES[league]
        season_code = self._season_code(season)
        url = f"https://www.football-data.co.uk/mmz4281/{season_code}/{league_code}.csv"

        response = httpx.get(url, timeout=15)
        response.raise_for_status()

        dest.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=dest.parent, suffix=".csv.tmp")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(response.content)
            os.replace(tmp_path, dest)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    @staticmethod
    def _season_code(season: str) -> str:
        """
        Converts season string to football-data.co.uk format.
        "2025/26" -> "2526"
        "2024/25" -> "2425"
        Handles both "/" and "-" separators.
        """
        normalised = season.replace("/", "-")
        parts = normalised.split("-")
        if len(parts) == 2:
            start = parts[0][-2:]
            end = parts[1][-2:]
            return start + end
        # fallback: strip separators and take first 4 chars
        return season.replace("/", "").replace("-", "")[:4]
