"""Ciemny/jasny pasek tytułu okna na Windows (DWM) — czysty ctypes.

Warstwa 1 kitu: kod wspólny dla obu torów GUI (Qt i tkinter), więc **ZERO
importów Qt ani tk**. Operuje na surowym uchwycie okna ``hwnd`` (int) — tor Qt
podaje ``int(window.winId())``, tor tkinter ``GetParent(winfo_id())``.

Na Windows pasek tytułu rysuje system (DWM), nie aplikacja — kolorujemy go przez
``DwmSetWindowAttribute``. Poza Windows funkcje są bezpiecznymi no-opami z logiem
``DEBUG``.

⚠️ Pułapka (GUI_STANDARD v2.5): atrybut ``DWMWA_USE_IMMERSIVE_DARK_MODE`` jest
**stanowy** — raz ustawiony, trzyma wartość aż do następnego jawnego ustawienia.
Dlatego wołający (``qt/titlebar.py``) ustawia go **BEZWARUNKOWO** na motyw
aplikacji przy każdym ``apply()``; ten moduł sam nie podejmuje decyzji „czy".
"""

from __future__ import annotations

import ctypes
import logging
import sys
from typing import Any

logger = logging.getLogger(__name__)

# Atrybuty DWM: 20 = nowsze Win10/Win11, 19 = starsze buildy Win10.
_DWMWA_USE_IMMERSIVE_DARK_MODE = 20
_DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19

# WinAPI do wymuszenia przemalowania ramki okna (pasek tytułu).
_WM_NCACTIVATE = 0x0086
# SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED
_SWP_FRAME_REDRAW = 0x0001 | 0x0002 | 0x0004 | 0x0010 | 0x0020


def set_titlebar(hwnd: int, dark: bool) -> None:
    """Ustawia ciemny (``dark=True``) lub jasny pasek tytułu okna.

    Poza Windows jest bezpiecznym no-opem (log ``DEBUG``). Wszystkie błędy
    ctypes/DWM (brak API, zły uchwyt) są wyciszane do ``WARNING`` — kolor belki
    to kosmetyka, nie wolno jej wywracać aplikacji.

    Args:
        hwnd: surowy uchwyt okna systemu (``int(window.winId())`` w Qt).
        dark: czy pasek ma być ciemny.
    """
    if sys.platform != "win32":
        logger.debug("set_titlebar: no-op poza Windows (hwnd=%s, dark=%s)", hwnd, dark)
        return
    _set_titlebar_win(hwnd, dark)


def _set_titlebar_win(hwnd: int, dark: bool) -> None:
    """Windowsowa implementacja ustawienia koloru paska tytułu."""
    try:
        value = ctypes.c_int(1 if dark else 0)
        # getattr: ``ctypes.windll`` istnieje tylko na Windows (czysty mypy cross-platform).
        windll: Any = getattr(ctypes, "windll")  # noqa: B009
        dwm = windll.dwmapi
        dwm.DwmSetWindowAttribute.restype = ctypes.c_long
        hr = dwm.DwmSetWindowAttribute(
            hwnd, _DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value)
        )
        if hr != 0:  # starszy build Win10 — spróbuj atrybutu 19
            dwm.DwmSetWindowAttribute(
                hwnd, _DWMWA_USE_IMMERSIVE_DARK_MODE_OLD, ctypes.byref(value), ctypes.sizeof(value)
            )
        _force_frame_redraw(windll, hwnd)
    except Exception as exc:
        # Różne błędy ctypes/DWM (brak API, zły HWND) — jednolicie jako brak wsparcia.
        logger.warning("Nie udało się ustawić koloru paska tytułu: %s", exc)


def _force_frame_redraw(windll: Any, hwnd: int) -> None:
    """Wymusza przemalowanie obszaru nieklienckiego (pasek tytułu).

    Bez mrugania oknem: dezaktywacja/aktywacja paska (``WM_NCACTIVATE`` 0→1) plus
    ``SetWindowPos`` z ``SWP_FRAMECHANGED``. Naprawia sytuację, gdy na Win10
    pasek tytułu nie odświeża się po zmianie motywu.
    """
    user32 = windll.user32
    user32.SendMessageW(hwnd, _WM_NCACTIVATE, 0, 0)
    user32.SendMessageW(hwnd, _WM_NCACTIVATE, 1, 0)
    user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, _SWP_FRAME_REDRAW)
