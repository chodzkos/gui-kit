"""Pasek tytułu okien tkinter = motyw aplikacji (DWM, GUI_STANDARD §3 + v2.5).

Cienka warstwa tkinter nad :func:`chodzkos_gui_kit.winutil.dwm.set_titlebar` —
analogiczna do toru Qt (``qt/titlebar.py``), ten sam wspólny kod ctypes DWM.

Różnica wobec Qt: ``winfo_id()`` zwraca uchwyt *dziecka*, więc prawdziwy HWND
ramki trzeba wyłuskać przez ``GetParent`` (pułapka z §3). To jedyny ctypes tutaj
i dotyczy WYŁĄCZNIE pobrania HWND z okna tkinter — samego DWM (atrybut + redraw
ramki) NIE duplikujemy, robi to ``winutil.dwm``.

Reguła v2.5 (atrybut DWM jest stanowy): kolor belki ustawiamy BEZWARUNKOWO wg
motywu aplikacji. W torze tkinter i tak nie ma auto-podążania za systemem (jak
``colorScheme()`` w Qt), więc bezwarunkowość jest tu naturalna.

Timing (§3): stosuj po pełnym zmapowaniu okna — ``window.after(10, ...)`` albo
przed pierwszym ``deiconify``. ``set_titlebar_dark`` woła ``update_idletasks()``,
by HWND był już wiarygodny.
"""

from __future__ import annotations

import ctypes
import sys
import tkinter as tk
from typing import TYPE_CHECKING, Any

from chodzkos_gui_kit.winutil import dwm

if TYPE_CHECKING:
    from chodzkos_gui_kit.tk.theme import ThemeName


def set_titlebar_dark(window: tk.Misc, dark: bool) -> None:
    """Ustawia ciemny/jasny pasek tytułu okna tkinter (przez wspólny ``winutil.dwm``).

    Poza Windows jest no-opem — ``winfo_id()`` nie jest tam HWND-em, a ``dwm``
    i tak nic nie robi.
    """
    if sys.platform != "win32":
        return
    hwnd = _window_hwnd(window)
    if hwnd is not None:
        dwm.set_titlebar(hwnd, dark)


def sync_titlebar(window: tk.Misc, mode: ThemeName) -> None:
    """Ustawia pasek tytułu okna na motyw aplikacji — BEZWARUNKOWO (v2.5)."""
    set_titlebar_dark(window, mode == "dark")


def _window_hwnd(window: tk.Misc) -> int | None:
    """Zwraca HWND ramki okna: ``GetParent(winfo_id())`` (tylko Windows).

    ``winfo_id()`` zwraca uchwyt dziecka — prawdziwą ramkę (z paskiem tytułu)
    daje dopiero ``GetParent``. ``update_idletasks`` gwarantuje, że okno jest już
    zmapowane i uchwyt wiarygodny.
    """
    try:
        window.update_idletasks()
        # getattr: ``ctypes.windll`` istnieje tylko na Windows (czysty mypy cross-platform).
        windll: Any = getattr(ctypes, "windll")  # noqa: B009
        return int(windll.user32.GetParent(window.winfo_id()))
    except Exception:
        # Błędy ctypes/Tk (brak okna, zły uchwyt) — kolor belki to kosmetyka.
        return None
