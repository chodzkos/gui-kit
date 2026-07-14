"""Testy :func:`make_scrollable` (warstwa qt/widgets) — offscreen, marker qt."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QScrollArea
from pytestqt.qtbot import QtBot

from chodzkos_gui_kit.qt.widgets import make_scrollable

pytestmark = pytest.mark.qt


def test_make_scrollable_wraps_and_configures(qtbot: QtBot) -> None:
    """Zwraca bezramkowy ``QScrollArea`` owijający ``content``, scroll pionowy w razie potrzeby."""
    content = QLabel("treść")
    qtbot.addWidget(content)

    area = make_scrollable(content)
    qtbot.addWidget(area)

    assert isinstance(area, QScrollArea)
    assert area.widget() is content
    assert area.widgetResizable() is True
    assert area.frameShape() == QFrame.Shape.NoFrame
    # Poziomy pasek wyłączony (dopasowanie szerokości), pionowy w razie potrzeby.
    assert area.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert area.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded


def test_make_scrollable_leaves_background_to_theme(qtbot: QtBot) -> None:
    """Tło niesie paleta motywu — ``autoFillBackground`` wyłączone na obszarze i viewportcie.

    (Uwaga: ``QScrollArea.setWidget`` z powrotem włącza ``autoFillBackground`` na
    samej zawartości, więc sprawdzamy powierzchnie, które faktycznie niosą tło —
    obszar i viewport.)
    """
    content = QLabel("treść")
    qtbot.addWidget(content)

    area = make_scrollable(content)
    qtbot.addWidget(area)

    assert area.autoFillBackground() is False
    assert area.viewport().autoFillBackground() is False
    assert not area.viewport().testAttribute(Qt.WidgetAttribute.WA_StyledBackground)
