import json
from datetime import datetime
from unittest.mock import patch

import pytest

from app.cache import load_last_processed, save_last_processed


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path):
    cache_file = tmp_path / "last_processed.json"
    with patch("app.cache._CACHE_FILE", cache_file):
        yield cache_file


class TestLoadLastProcessed:
    def test_returns_none_when_file_does_not_exist(self):
        result = load_last_processed()

        assert result is None

    def test_returns_dict_after_save(self):
        save_last_processed(12345, datetime(2026, 5, 10, 7, 0, 0))

        result = load_last_processed()

        assert isinstance(result, dict)

    def test_returns_correct_activity_id(self):
        save_last_processed(99999, datetime(2026, 5, 10, 7, 0, 0))

        result = load_last_processed()

        assert result["activity_id"] == 99999

    def test_returns_datetime_object_for_start_date_local(self):
        save_last_processed(1, datetime(2026, 5, 10, 7, 30, 15))

        result = load_last_processed()

        assert isinstance(result["start_date_local"], datetime)

    def test_round_trips_datetime_correctly(self):
        original = datetime(2026, 5, 10, 7, 30, 15)
        save_last_processed(1, original)

        result = load_last_processed()

        assert result["start_date_local"] == original


class TestSaveLastProcessed:
    def test_creates_parent_directory(self, tmp_path):
        nested = tmp_path / "deep" / "dir" / "last_processed.json"
        with patch("app.cache._CACHE_FILE", nested):
            save_last_processed(1, datetime(2026, 5, 10, 7, 0, 0))

        assert nested.exists()

    def test_writes_valid_json(self, isolated_cache):
        save_last_processed(42, datetime(2026, 5, 10, 7, 0, 0))

        data = json.loads(isolated_cache.read_text())
        assert "activity_id" in data
        assert "start_date_local" in data

    def test_overwrites_previous_cache(self):
        save_last_processed(1, datetime(2026, 5, 1, 6, 0, 0))
        save_last_processed(2, datetime(2026, 5, 10, 7, 0, 0))

        result = load_last_processed()

        assert result["activity_id"] == 2
        assert result["start_date_local"] == datetime(2026, 5, 10, 7, 0, 0)
