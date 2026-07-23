"""Testy generycznej konfiguracji — muszą przechodzić bez PySide6 (warstwa 0)."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import pytest

from chodzkos_gui_kit import config as config_mod
from chodzkos_gui_kit.config import Config, config_dir, load_config, save_config


def test_config_dir_uses_platformdirs(monkeypatch) -> None:
    """Poza trybem portable lokalizacja pochodzi z platformdirs (nazwa appki w ścieżce)."""
    monkeypatch.setattr(config_mod, "_is_portable", lambda: False)
    path = config_dir("myapp")
    assert "myapp" in str(path)


def test_load_missing_returns_empty(tmp_path: Path) -> None:
    """Brak pliku → pusty słownik (nie wyjątek)."""
    assert load_config(tmp_path / "nie_ma.json") == {}


def test_load_corrupt_backs_up_and_warns(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Uszkodzony JSON → {} + kopia ``config.json.broken-*`` obok + warning (nie po cichu)."""
    bad = tmp_path / "config.json"
    bad.write_text("{ to nie json", encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="chodzkos_gui_kit.config"):
        assert load_config(bad) == {}

    # Uszkodzony plik przeniesiony (nie kasowany po cichu), oryginał już nie istnieje.
    assert not bad.exists()
    backups = list(tmp_path.glob("config.json.broken-*"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "{ to nie json"
    assert any("start z domyślnych" in rec.message for rec in caplog.records)


def test_load_corrupt_keeps_previous_backup(tmp_path: Path) -> None:
    """Kolejna awaria nie nadpisuje wcześniejszej kopii (współistnieją)."""
    bad = tmp_path / "config.json"
    # Pierwsza kopia z tym samym „second-timestamp" już leży obok.
    (tmp_path / f"config.json.broken-{time.strftime('%Y%m%d-%H%M%S')}").write_text("stara")
    bad.write_text("{ znowu zle", encoding="utf-8")
    assert load_config(bad) == {}
    assert len(list(tmp_path.glob("config.json.broken-*"))) == 2


def test_save_is_atomic_and_roundtrips(tmp_path: Path) -> None:
    """Zapis tworzy katalogi, jest atomowy (tmp+replace) i wczytuje się z powrotem."""
    target = tmp_path / "nested" / "config.json"
    save_config(target, {"theme": "dark", "ą": "ę"})
    assert json.loads(target.read_text(encoding="utf-8")) == {"theme": "dark", "ą": "ę"}
    assert not (tmp_path / "nested" / "config.json.tmp").exists()
    assert load_config(target) == {"theme": "dark", "ą": "ę"}


def test_config_loads_existing_clean(tmp_path: Path) -> None:
    """Config startuje czysty z danych na dysku (init nie woła __setitem__)."""
    path = tmp_path / "config.json"
    save_config(path, {"theme": "light"})
    config = Config("myapp", path=path)
    assert config.get("theme") == "light"
    assert config["theme"] == "light"
    assert config.dirty is False


def test_set_marks_dirty_and_fires_on_dirty(tmp_path: Path) -> None:
    """set/__setitem__ oznacza brudne i woła on_dirty (hak debounce GUI)."""
    fired: list[int] = []
    config = Config("myapp", path=tmp_path / "config.json", on_dirty=lambda: fired.append(1))
    assert config.dirty is False

    config.set("theme", "dark")
    assert config.dirty is True
    assert config.get("theme") == "dark"
    assert fired == [1]

    config["lang"] = "pl"  # styl słownikowy działa tak samo
    assert fired == [1, 1]


def test_flush_writes_only_when_dirty(tmp_path: Path) -> None:
    """flush zapisuje tylko gdy są zmiany; save_now czyści flagę."""
    path = tmp_path / "config.json"
    config = Config("myapp", path=path)

    config.flush()  # nic nie brudne → nie powinno powstać nic do zapisania
    assert not path.exists()

    config.set("theme", "dark")
    config.flush()
    assert load_config(path) == {"theme": "dark"}
    assert config.dirty is False

    config.save_now()  # bezwarunkowy zapis, flaga czysta
    assert config.dirty is False
