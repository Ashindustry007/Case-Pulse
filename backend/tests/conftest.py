"""Test fixtures: every test gets its own throwaway SQLite DB (settings.db_path is redirected)."""
from __future__ import annotations

import pytest

from backend.app import config, db


@pytest.fixture()
def tmp_db(tmp_path, monkeypatch):
    path = tmp_path / "test.db"
    s = config.Settings(db_path=path, data_dir=tmp_path)
    monkeypatch.setattr(config, "settings", s)  # db.py and data-dir users read config.settings at call time
    db.migrate(path)
    return path


@pytest.fixture()
def fake_clio():
    from backend.tests.fake_clio import FakeClio

    return FakeClio()
