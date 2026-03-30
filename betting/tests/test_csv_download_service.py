"""Tests for CsvDownloadService."""

import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from betting.services.csv_download_service import CsvDownloadService


@pytest.fixture
def cache_dir(tmp_path):
    return str(tmp_path / "csv_cache")


def _make_service(cache_dir: str, max_age_hours: int = 24) -> CsvDownloadService:
    return CsvDownloadService(cache_dir=cache_dir, max_age_hours=max_age_hours)


def _write_cache(service: CsvDownloadService, league: str, season: str, content: str = "data") -> Path:
    dest = service._cache_path(league, season)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    meta_path = dest.with_suffix(".meta")
    meta_path.write_text(datetime.utcnow().isoformat(), encoding="utf-8")
    return dest


class TestCacheBehaviour:
    def test_returns_cached_file_when_fresh(self, cache_dir):
        service = _make_service(cache_dir)
        dest = _write_cache(service, "PL", "2024/25")

        with patch("httpx.get") as mock_get:
            result = service.get("PL", "2024/25")

        mock_get.assert_not_called()
        assert result == str(dest)

    def test_redownloads_when_stale(self, cache_dir):
        service = _make_service(cache_dir, max_age_hours=0)
        dest = _write_cache(service, "PL", "2024/25")

        mock_response = MagicMock()
        mock_response.content = b"fresh,csv,data\n"
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.get", return_value=mock_response) as mock_get:
            result = service.get("PL", "2024/25")

        mock_get.assert_called_once()
        assert result == str(dest)
        assert dest.read_bytes() == b"fresh,csv,data\n"

    def test_stale_fallback_on_download_failure(self, cache_dir):
        service = _make_service(cache_dir, max_age_hours=0)
        dest = _write_cache(service, "PL", "2024/25", content="stale,data\n")

        with patch("httpx.get", side_effect=httpx.ConnectError("timeout")):
            result = service.get("PL", "2024/25")

        assert result == str(dest)
        assert dest.read_text() == "stale,data\n"

    def test_raises_when_download_fails_and_no_cache(self, cache_dir):
        service = _make_service(cache_dir)

        with patch("httpx.get", side_effect=httpx.ConnectError("timeout")):
            with pytest.raises(httpx.ConnectError):
                service.get("PL", "2024/25")

    def test_creates_cache_dir_on_instantiation(self, tmp_path):
        new_cache = str(tmp_path / "new_cache_dir")
        assert not Path(new_cache).exists()
        _make_service(new_cache)
        assert Path(new_cache).exists()


class TestSeasonCode:
    @pytest.mark.parametrize("season,expected", [
        ("2025/26", "2526"),
        ("2024/25", "2425"),
        ("2023/24", "2324"),
        ("2025-26", "2526"),
        ("2024-25", "2425"),
    ])
    def test_season_code_derivation(self, season, expected):
        assert CsvDownloadService._season_code(season) == expected


class TestDownload:
    def test_download_success_writes_to_dest(self, cache_dir):
        service = _make_service(cache_dir)

        mock_response = MagicMock()
        mock_response.content = b"HomeTeam,AwayTeam,FTHG,FTAG\n"
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.get", return_value=mock_response):
            result = service.get("PL", "2024/25")

        dest = service._cache_path("PL", "2024/25")
        assert result == str(dest)
        assert dest.read_bytes() == b"HomeTeam,AwayTeam,FTHG,FTAG\n"

    def test_raises_for_unsupported_league(self, cache_dir):
        service = _make_service(cache_dir)

        with pytest.raises(ValueError, match="not supported"):
            service.get("UnknownLeague", "2024/25")

    def test_uses_correct_url(self, cache_dir):
        service = _make_service(cache_dir)

        mock_response = MagicMock()
        mock_response.content = b"data\n"
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.get", return_value=mock_response) as mock_get:
            service.get("PL", "2024/25")

        called_url = mock_get.call_args[0][0]
        assert "mmz4281/2425/E0.csv" in called_url

    def test_uses_timeout_15(self, cache_dir):
        service = _make_service(cache_dir)

        mock_response = MagicMock()
        mock_response.content = b"data\n"
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.get", return_value=mock_response) as mock_get:
            service.get("PL", "2024/25")

        assert mock_get.call_args[1]["timeout"] == 15
