"""Pasek tytułu okien Qt = motyw aplikacji (DWM, GUI_STANDARD v2.5).

Cienka warstwa Qt nad :func:`chodzkos_gui_kit.winutil.dwm.set_titlebar` — wyciąga
``int(window.winId())`` i woła kod ctypes. ``winId()`` jest wiarygodny dopiero po
utworzeniu natywnego okna, więc :class:`TitlebarSync` re-aplikuje kolor belki
przy ``Show`` i ``ActivationChange``.

⚠️ Reguła v2.5 (atrybut DWM jest STANOWY): pasek tytułu ustawiamy
**BEZWARUNKOWO** na motyw aplikacji, na KAŻDYM oknie top-level, przy każdym
``apply()``. Nigdy nie pomijamy „bo motyw zgodny z systemem" — pominięcie
zostawia poprzednią wartość (sekwencja jasny→ciemny→jasny kończyłaby się czarną
belką). Rozróżnienie zgodność/rozjazd dotyczy WYŁĄCZNIE dialogów (patrz
:mod:`chodzkos_gui_kit.qt.dialogs`), nie belek.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QWidget

from chodzkos_gui_kit.winutil import dwm

if TYPE_CHECKING:
    from chodzkos_gui_kit.qt.theme import ThemeName


def set_titlebar_dark(window: QWidget, dark: bool) -> None:
    """Ustawia ciemny/jasny pasek tytułu okna przez DWM (uchwyt z ``winId``)."""
    dwm.set_titlebar(int(window.winId()), dark)


def sync_titlebar(window: QWidget, mode: ThemeName) -> None:
    """Ustawia pasek tytułu okna na motyw aplikacji — BEZWARUNKOWO (v2.5).

    Args:
        window: okno najwyższego poziomu (``QMainWindow``, ``QDialog``...).
        mode: faktycznie zastosowany motyw aplikacji (``"dark"``/``"light"``).
    """
    set_titlebar_dark(window, mode == "dark")


class TitlebarSync(QObject):
    """Filtr zdarzeń utrzymujący kolor paska tytułu okna na motywie aplikacji.

    Re-aplikuje DWM przy ``Show`` (pierwsze utworzenie natywnego okna → poprawny
    ``winId``) oraz ``ActivationChange`` (aktywacja potrafi zresetować belkę na
    Win10). Motyw pobiera leniwie z ``mode_getter`` — dzięki temu zawsze widzi
    bieżące ustawienie menedżera motywu.

    Args:
        window: okno do śledzenia; ``TitlebarSync`` zostaje jego dzieckiem.
        mode_getter: funkcja zwracająca bieżący motyw aplikacji (``ThemeName``).
    """

    def __init__(self, window: QWidget, mode_getter: Callable[[], ThemeName]) -> None:
        super().__init__(window)
        self._window = window
        self._mode_getter = mode_getter
        window.installEventFilter(self)

    def refresh(self) -> None:
        """Ustawia pasek tytułu okna na bieżący motyw (bezwarunkowo)."""
        sync_titlebar(self._window, self._mode_getter())

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802 — Qt API
        """Re-aplikuje kolor belki przy pokazaniu i (de)aktywacji okna."""
        if event.type() in (QEvent.Type.Show, QEvent.Type.ActivationChange):
            self.refresh()
        return False
