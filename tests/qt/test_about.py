"""Testy widgetu :class:`AboutPanel` (warstwa qt/widgets) — offscreen, marker qt.

Sprawdzanie aktualizacji jest wstrzykiwane (bez sieci): fałszywy ``check_update``
zwraca deterministyczny wynik, a test czeka na sygnał wątku.
"""

from __future__ import annotations

import pytest
from PySide6.QtGui import QPixmap
from pytestqt.qtbot import QtBot

from chodzkos_gui_kit.qt.widgets.about import AboutPanel, AboutTexts

pytestmark = pytest.mark.qt


def _labels(panel: AboutPanel) -> list[str]:
    from PySide6.QtWidgets import QLabel

    return [w.text() for w in panel.findChildren(QLabel)]


def test_renders_name_version_and_links(qtbot: QtBot) -> None:
    """Nazwa, wersja (szablon) i linki trafiają do etykiet."""
    panel = AboutPanel(
        app_name="IcoForge",
        version="1.3.0",
        links=[("github.com/chodzkos/icoforge", "https://github.com/chodzkos/icoforge")],
        license_name="MIT",
        texts=AboutTexts(version_label="Wersja {version}", license_label="Licencja: {name}"),
    )
    qtbot.addWidget(panel)
    texts = " | ".join(_labels(panel))
    assert "IcoForge" in texts
    assert "Wersja 1.3.0" in texts
    assert "Licencja: MIT" in texts
    assert 'href="https://github.com/chodzkos/icoforge"' in texts


def test_no_update_row_without_check(qtbot: QtBot) -> None:
    """Bez ``check_update`` nie ma wiersza statusu aktualizacji."""
    panel = AboutPanel(app_name="App", version="1.0.0")
    qtbot.addWidget(panel)
    assert all("update" not in t.lower() and "aktualiz" not in t.lower() for t in _labels(panel))


def test_update_available_sets_link(qtbot: QtBot) -> None:
    """Dostępna aktualizacja → link do strony wydań z nową wersją."""
    panel = AboutPanel(
        app_name="App",
        version="1.0.0",
        check_update=lambda: (True, "2.0.0"),
        releases_url="https://example.test/releases",
        texts=AboutTexts(update_available="Nowa: {version}"),
    )
    qtbot.addWidget(panel)
    # start_update_check jest idempotentny — wołamy wprost, by nie zależeć od timingu
    # showEvent; waitUntil pollinguje etykietę (wynik wątku może przyjść zanim
    # zaczęlibyśmy nasłuch sygnału — stąd nie waitSignal).
    panel.start_update_check()
    qtbot.waitUntil(lambda: "Nowa: 2.0.0" in " | ".join(_labels(panel)), timeout=3000)
    joined = " | ".join(_labels(panel))
    assert 'href="https://example.test/releases"' in joined
    panel.stop_update_check()


def test_up_to_date_message(qtbot: QtBot) -> None:
    """Brak aktualizacji → komunikat „masz najnowszą"."""
    panel = AboutPanel(
        app_name="App",
        version="2.0.0",
        check_update=lambda: (False, ""),
        texts=AboutTexts(up_to_date="Najnowsza."),
    )
    qtbot.addWidget(panel)
    panel.start_update_check()
    qtbot.waitUntil(lambda: "Najnowsza." in " | ".join(_labels(panel)), timeout=3000)
    panel.stop_update_check()


def test_logo_variant_reloads_on_palette_change(qtbot: QtBot) -> None:
    """Logo funkcyjne jest przeładowywane przy ``PaletteChange``."""
    calls = {"n": 0}

    def _logo() -> QPixmap:
        calls["n"] += 1
        pix = QPixmap(10, 10)
        pix.fill()
        return pix

    panel = AboutPanel(app_name="App", version="1.0.0", logo=_logo)
    qtbot.addWidget(panel)
    before = calls["n"]
    assert before >= 1  # ustawione w konstruktorze
    from PySide6.QtCore import QEvent

    panel.changeEvent(QEvent(QEvent.Type.PaletteChange))
    assert calls["n"] == before + 1
