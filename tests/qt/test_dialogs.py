"""Testy helperów dialogów plików (natywny vs ciemny dialog Qt wg motywu)."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QFileDialog, QToolButton
from pytestqt.qtbot import QtBot

from chodzkos_gui_kit import palette as pal
from chodzkos_gui_kit.qt import dialogs

pytestmark = pytest.mark.qt


@pytest.mark.parametrize(
    ("app_mode", "system", "expected_native"),
    [
        ("dark", "dark", True),  # zgodność → natywny
        ("light", "light", True),  # zgodność → natywny
        ("dark", "light", False),  # rozjazd → dialog Qt
        ("light", "dark", False),  # rozjazd (w obie strony) → dialog Qt
    ],
)
def test_use_native_dialog_symmetric_mismatch(
    app_mode: str, system: str, expected_native: bool
) -> None:
    """Natywny ⇔ motyw aplikacji == motyw systemu; przy KAŻDYM rozjeździe → Qt (§4)."""
    assert dialogs.use_native_dialog(app_mode, system) is expected_native  # type: ignore[arg-type]


def test_auto_mode_always_uses_native(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tryb auto: motyw aplikacji podąża za systemem → zgodność → zawsze natywny.

    Mockujemy motyw systemu i ustawiamy efektywny motyw aplikacji na ten sam —
    decyzja nie może zależeć od motywu maszyny CI.
    """
    for system in ("dark", "light"):
        palette = pal.DARK if system == "dark" else pal.LIGHT
        monkeypatch.setattr(dialogs, "current_palette", lambda p=palette: p)
        monkeypatch.setattr(dialogs, "system_scheme", lambda s=system: s)
        assert dialogs._native() is True


def test_open_file_native_delegates(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    """Gdy decyzja = natywny, helper używa ``getOpenFileName``."""
    monkeypatch.setattr(dialogs, "_native", lambda: True)
    monkeypatch.setattr(
        dialogs.QFileDialog,
        "getOpenFileName",
        staticmethod(lambda *a, **k: ("/x/book.epub", "")),
    )
    assert dialogs.open_file(None, "Tytuł", "", "EPUB (*.epub)") == "/x/book.epub"


def test_open_file_qt_dialog_syncs_titlebar(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    """Gdy decyzja = Qt, helper buduje dialog i ustawia pasek tytułu na motyw app."""
    synced: list[str] = []
    monkeypatch.setattr(dialogs, "_native", lambda: False)
    monkeypatch.setattr(dialogs, "current_palette", lambda: pal.DARK)
    monkeypatch.setattr(dialogs, "sync_titlebar", lambda _w, mode: synced.append(mode))
    monkeypatch.setattr(dialogs.QFileDialog, "exec", lambda self: 1)
    monkeypatch.setattr(dialogs.QFileDialog, "selectedFiles", lambda self: ["/a/book.epub"])

    result = dialogs.open_file(None, "Tytuł", "", "EPUB (*.epub)")

    assert result == "/a/book.epub"
    assert synced == ["dark"]


def test_open_files_qt_cancelled_returns_empty(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Anulowany dialog Qt wielu plików zwraca pustą listę."""
    monkeypatch.setattr(dialogs, "_native", lambda: False)
    monkeypatch.setattr(dialogs, "sync_titlebar", lambda *a, **k: None)
    monkeypatch.setattr(dialogs.QFileDialog, "exec", lambda self: 0)
    assert dialogs.open_files(None, "Dodaj pliki", "Obsługiwane (*.epub)") == []


def test_pick_dir_native_delegates(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    """Gdy decyzja = natywny, wybór folderu używa ``getExistingDirectory``."""
    monkeypatch.setattr(dialogs, "_native", lambda: True)
    monkeypatch.setattr(
        dialogs.QFileDialog,
        "getExistingDirectory",
        staticmethod(lambda *a, **k: "/home/books"),
    )
    assert dialogs.pick_dir(None, "Dodaj folder") == "/home/books"


def test_dark_dialog_has_sidebar_and_detail_view(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fallbackowy dialog Qt ma niepusty pasek boczny i widok szczegółowy."""
    monkeypatch.setattr(dialogs, "sync_titlebar", lambda *a, **k: None)
    dialog = dialogs._dark_dialog(None, "Tytuł", "", None)
    qtbot.addWidget(dialog)
    assert dialog.viewMode() == QFileDialog.ViewMode.Detail
    assert dialog.sidebarUrls()  # co najmniej dyski (QDir.drives)


def test_dark_dialog_restores_size_and_persists_on_run(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rozmiar okna jest odtwarzany z configu i zapisywany po zamknięciu dialogu."""
    monkeypatch.setattr(dialogs, "sync_titlebar", lambda *a, **k: None)
    config: dict[str, object] = {"file_dialog_size": [820, 600]}
    dialog = dialogs._dark_dialog(None, "Tytuł", "", config)
    qtbot.addWidget(dialog)
    assert (dialog.size().width(), dialog.size().height()) == (820, 600)

    dialog.resize(910, 540)
    monkeypatch.setattr(dialog, "exec", lambda: 0)  # anulowanie
    dialogs._first_selected(dialog, config)
    assert config["file_dialog_size"] == [910, 540]


def test_dark_dialog_toolbar_buttons_get_icon_and_unclipped(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Przyciski nawigacji dostają ikonę, a przycinający app-owy padding jest zdjęty (v2.6).

    To była przyczyna „pustych przycisków" — w 22 px przycisku padding 4px 12px
    z app-QSS przycinał ikonę do zera. Test geometryczny/stanowy, nie pikselowy.
    """
    monkeypatch.setattr(dialogs, "sync_titlebar", lambda *a, **k: None)
    dialog = dialogs._dark_dialog(None, "Tytuł", "", None)
    qtbot.addWidget(dialog)
    dialogs._force_toolbar_buttons(dialog)  # w produkcji wołane tuż przed exec()
    for name in dialogs._NAV_ICONS:
        button = dialog.findChild(QToolButton, name)
        assert button is not None
        assert not button.icon().isNull()
        assert "padding: 1px" in button.styleSheet()  # ciężki padding zneutralizowany
