"""Testy paska tytułu okna (DWM) — bezwarunkowe ustawianie (atrybut stanowy)."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QWidget
from pytestqt.qtbot import QtBot

from chodzkos_gui_kit.qt import titlebar

pytestmark = pytest.mark.qt


def test_set_titlebar_dark_delegates_to_winutil(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    """set_titlebar_dark przekazuje winId i flagę do warstwy ctypes (winutil.dwm)."""
    calls: list[tuple[int, bool]] = []
    monkeypatch.setattr(titlebar.dwm, "set_titlebar", lambda hwnd, dark: calls.append((hwnd, dark)))
    widget = QWidget()
    qtbot.addWidget(widget)

    titlebar.set_titlebar_dark(widget, True)
    assert len(calls) == 1
    hwnd, dark = calls[0]
    assert hwnd == int(widget.winId())
    assert dark is True


def test_sync_titlebar_maps_mode_to_bool(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    """sync_titlebar mapuje motyw na flagę DWM (dark→True, light→False)."""
    calls: list[bool] = []
    monkeypatch.setattr(titlebar.dwm, "set_titlebar", lambda _hwnd, dark: calls.append(dark))
    widget = QWidget()
    qtbot.addWidget(widget)

    titlebar.sync_titlebar(widget, "dark")
    titlebar.sync_titlebar(widget, "light")
    assert calls == [True, False]


def test_sync_titlebar_is_unconditional_stateful_regression(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    """jasny→ciemny→jasny: ostatnie ustawienie to dark=False (regresja stanowości v2.5).

    Atrybut DWM jest stanowy — gdyby sync_titlebar pomijał ustawianie „bo motyw
    zgodny z systemem", końcowy jasny zostawiłby belkę ciemną.
    """
    calls: list[bool] = []
    monkeypatch.setattr(titlebar.dwm, "set_titlebar", lambda _hwnd, dark: calls.append(dark))
    widget = QWidget()
    qtbot.addWidget(widget)

    titlebar.sync_titlebar(widget, "light")
    titlebar.sync_titlebar(widget, "dark")
    titlebar.sync_titlebar(widget, "light")

    assert calls == [False, True, False]
    assert calls[-1] is False


def test_titlebar_sync_reapplies_on_show_and_activation(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    """TitlebarSync re-aplikuje DWM przy Show i ActivationChange (winId po showEvent)."""
    calls: list[bool] = []
    monkeypatch.setattr(titlebar.dwm, "set_titlebar", lambda _hwnd, dark: calls.append(dark))
    widget = QWidget()
    qtbot.addWidget(widget)

    mode = {"value": "dark"}
    sync = titlebar.TitlebarSync(widget, lambda: mode["value"])  # type: ignore[arg-type, return-value]

    # Zdarzenie Show → sync wg bieżącego motywu (filtr nie konsumuje zdarzenia).
    assert sync.eventFilter(widget, QEvent(QEvent.Type.Show)) is False
    assert calls and calls[-1] is True

    # Zmiana motywu + ActivationChange → ponowne ustawienie wg nowej wartości.
    mode["value"] = "light"
    sync.eventFilter(widget, QEvent(QEvent.Type.ActivationChange))
    assert calls[-1] is False

    # Zdarzenie spoza listy (np. Resize) nie rusza belki.
    before = len(calls)
    sync.eventFilter(widget, QEvent(QEvent.Type.Resize))
    assert len(calls) == before

    # Bezpośredni refresh działa tak samo.
    sync.refresh()
    assert calls[-1] is False
