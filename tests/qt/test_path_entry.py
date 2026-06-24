"""Testy widgetu :class:`PathEntry` (warstwa qt/widgets) — offscreen, marker qt."""

from __future__ import annotations

from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot

from chodzkos_gui_kit.qt.widgets import path_entry
from chodzkos_gui_kit.qt.widgets.path_entry import PathEntry, PathEntryTexts

pytestmark = pytest.mark.qt


@pytest.mark.parametrize(
    ("mode", "tooltip"),
    [
        ("dir", "Choose folder"),
        ("file", "Choose file"),
        ("save", "Choose save location"),
    ],
)
def test_construct_modes(qtbot: QtBot, mode: str, tooltip: str) -> None:
    """Konstrukcja w 3 trybach: tooltip przycisku wg trybu (domyślne ang.)."""
    widget = PathEntry(mode=mode)  # type: ignore[arg-type]
    qtbot.addWidget(widget)
    assert widget.mode == mode
    assert widget.button.toolTip() == tooltip


def test_get_set_roundtrip(qtbot: QtBot) -> None:
    """``set``/``get`` round-trip; ``get`` przycina białe znaki."""
    widget = PathEntry()
    qtbot.addWidget(widget)
    widget.set("  /tmp/x  ")
    assert widget.get() == "/tmp/x"


def test_path_changed_emitted_on_settext(qtbot: QtBot) -> None:
    """``path_changed`` emituje przy zmianie tekstu pola."""
    widget = PathEntry()
    qtbot.addWidget(widget)
    received: list[str] = []
    widget.path_changed.connect(received.append)
    widget.entry.setText("/a/b")
    assert received == ["/a/b"]


def test_start_dir_file_returns_parent(qtbot: QtBot, tmp_path: Path) -> None:
    """Dla ścieżki pliku katalog startowy to katalog nadrzędny."""
    widget = PathEntry(mode="file")
    qtbot.addWidget(widget)
    widget.set(str(tmp_path / "doc.txt"))
    assert widget._start_dir() == str(tmp_path)


def test_start_dir_existing_dir_returns_itself(qtbot: QtBot, tmp_path: Path) -> None:
    """Dla istniejącego katalogu katalog startowy to on sam."""
    widget = PathEntry(mode="dir")
    qtbot.addWidget(widget)
    widget.set(str(tmp_path))
    assert widget._start_dir() == str(tmp_path)


def test_remember_writes_to_config_and_is_reused(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``remember_key`` zapisuje katalog wyboru do configu i czyta go potem."""
    config: dict[str, object] = {}
    widget = PathEntry(mode="dir", config=config, remember_key="last")
    qtbot.addWidget(widget)
    chosen = tmp_path / "out"
    chosen.mkdir()
    monkeypatch.setattr(path_entry, "pick_dir", lambda *a, **k: str(chosen))

    widget._browse()
    assert widget.get() == str(chosen)
    assert config["last"] == str(chosen)

    # przy pustym polu start_dir bierze zapamiętany katalog z configu
    widget.set("")
    assert widget._start_dir() == str(chosen)


def test_browse_file_passes_built_filter(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    """Tryb file woła ``open_file`` z filtrem zbudowanym z ``filetypes``."""
    widget = PathEntry(mode="file", filetypes=[("Text", "*.txt"), ("All", "*.*")])
    qtbot.addWidget(widget)
    captured: dict[str, str] = {}

    def fake_open_file(parent: object, title: str, start_dir: str, flt: str, cfg: object) -> str:
        captured["title"] = title
        captured["filter"] = flt
        return "/picked.txt"

    monkeypatch.setattr(path_entry, "open_file", fake_open_file)
    widget._browse()
    assert widget.get() == "/picked.txt"
    assert captured["title"] == "Choose file"
    assert captured["filter"] == "Text (*.txt);;All (*.*)"


def test_custom_texts_override_defaults(qtbot: QtBot) -> None:
    """Aplikacja może podać przetłumaczone teksty przez ``PathEntryTexts``."""
    texts = PathEntryTexts(tooltip_dir="Wybierz folder", title_dir="Wybierz folder")
    widget = PathEntry(mode="dir", texts=texts)
    qtbot.addWidget(widget)
    assert widget.button.toolTip() == "Wybierz folder"
    assert widget._dialog_title() == "Wybierz folder"
