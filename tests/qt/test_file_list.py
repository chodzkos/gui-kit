"""Testy widgetu :class:`FileList` (warstwa qt/widgets) — offscreen, marker qt."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QUrl
from pytestqt.qtbot import QtBot

from chodzkos_gui_kit.qt.widgets import file_list as fl_mod
from chodzkos_gui_kit.qt.widgets.file_list import FileList

pytestmark = pytest.mark.qt


def test_add_files_filters_dedup_and_confirm(qtbot: QtBot, tmp_path: Path) -> None:
    """add_files: filtr rozszerzeń + dedup + hook confirm."""
    rejected = tmp_path / "skip.epub"
    fl = FileList(extensions={".epub"}, confirm=lambda p: p != rejected)
    qtbot.addWidget(fl)

    fl.add_files(
        [
            tmp_path / "a.epub",
            tmp_path / "a.epub",  # duplikat
            tmp_path / "b.txt",  # zły ext
            rejected,  # odrzucony przez confirm
        ]
    )
    assert fl.files() == [tmp_path / "a.epub"]


def test_files_returns_paths_from_str_input(qtbot: QtBot, tmp_path: Path) -> None:
    """Wejście str jest normalizowane — files() zwraca list[Path]."""
    fl = FileList(extensions={".epub"})
    qtbot.addWidget(fl)
    fl.add_files([str(tmp_path / "a.epub")])
    result = fl.files()
    assert result == [tmp_path / "a.epub"]
    assert all(isinstance(p, Path) for p in result)


def test_no_extensions_accepts_everything(qtbot: QtBot, tmp_path: Path) -> None:
    """Bez extensions lista przyjmuje dowolne pliki."""
    fl = FileList()
    qtbot.addWidget(fl)
    fl.add_files([tmp_path / "a.epub", tmp_path / "b.xyz"])
    assert fl.files() == [tmp_path / "a.epub", tmp_path / "b.xyz"]


def test_drop_folder_recurses(qtbot: QtBot, tmp_path: Path) -> None:
    """Upuszczenie folderu skanuje go rekurencyjnie (filtr rozszerzeń działa)."""
    (tmp_path / "top.epub").write_text("x", encoding="utf-8")
    nested = tmp_path / "sub"
    nested.mkdir()
    (nested / "deep.epub").write_text("x", encoding="utf-8")
    (nested / "ignore.txt").write_text("x", encoding="utf-8")

    fl = FileList(extensions={".epub"})
    qtbot.addWidget(fl)

    event = MagicMock()
    event.mimeData().urls.return_value = [QUrl.fromLocalFile(str(tmp_path))]
    fl.dropEvent(event)

    assert set(fl.files()) == {tmp_path / "top.epub", nested / "deep.epub"}
    event.acceptProposedAction.assert_called_once()


def test_current_path_and_select_first(qtbot: QtBot, tmp_path: Path) -> None:
    """current_path/select_first działają na widoku listy."""
    fl = FileList(extensions={".epub"})
    qtbot.addWidget(fl)
    assert fl.current_path() is None
    fl.add_files([tmp_path / "a.epub", tmp_path / "b.epub"])
    fl.select_first()
    assert fl.current_path() == tmp_path / "a.epub"


def test_signals_emit(qtbot: QtBot, tmp_path: Path) -> None:
    """files_changed niesie kopię listy; selection_changed niesie Path/None."""
    fl = FileList(extensions={".epub"})
    qtbot.addWidget(fl)

    files_seen: list[list[Path]] = []
    sel_seen: list[object] = []
    fl.files_changed.connect(files_seen.append)
    fl.selection_changed.connect(sel_seen.append)

    fl.add_files([tmp_path / "a.epub"])
    assert files_seen[-1] == [tmp_path / "a.epub"]

    fl.select_first()
    assert sel_seen[-1] == tmp_path / "a.epub"


def test_count_label_injected_and_default(qtbot: QtBot, tmp_path: Path) -> None:
    """Wstrzyknięty count_label woła się z liczbą; bez niego — domyślny ang."""
    default_fl = FileList()
    qtbot.addWidget(default_fl)
    assert default_fl.count_label.text() == "0 files"

    seen: list[int] = []

    def label(n: int) -> str:
        seen.append(n)
        return f"{n} plik(ów)"

    fl = FileList(extensions={".epub"}, count_label=label)
    qtbot.addWidget(fl)
    fl.add_files([tmp_path / "a.epub"])
    assert fl.count_label.text() == "1 plik(ów)"
    assert seen[-1] == 1


def test_add_files_dialog_uses_built_filter(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Przycisk „+Pliki" woła open_files z filtrem z rozszerzeń."""
    fl = FileList(extensions={".epub", ".txt"})
    qtbot.addWidget(fl)
    captured: dict[str, str] = {}

    def fake_open_files(parent: object, title: str, flt: str, cfg: object) -> list[str]:
        captured["title"] = title
        captured["filter"] = flt
        return [str(tmp_path / "a.epub")]

    monkeypatch.setattr(fl_mod, "open_files", fake_open_files)
    fl._add_files()
    assert captured["filter"] == "Supported (*.epub *.txt)"
    assert fl.files() == [tmp_path / "a.epub"]
