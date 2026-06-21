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

⚠️ Pułapka (GUI_STANDARD v2.9): uchwyt do ctypes ZAWSZE przez typ wskaźnikowy
(``wintypes.HWND`` / ``c_void_p``) + ustawione ``argtypes``. Goły Python int
marshaluje się domyślnie jako 32-bit ``c_int`` i **TRUNCUJE 64-bit HWND na Win64**
(objaw: DWM/titlebar działa na części okien, na innych nie).
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


def _configure_signatures(dwm: Any, user32: Any, hwnd_type: type) -> None:
    """Ustawia ``argtypes``/``restype`` dla wywołań DWM/user32 (uchwyt = ``hwnd_type``).

    KLUCZOWE: ``hwnd_type`` musi być typem WSKAŹNIKOWYM (``wintypes.HWND``, równe
    ``c_void_p`` na Windows). Bez ustawionych ``argtypes`` ctypes marshaluje goły
    Python int jako 32-bit ``c_int`` → **truncacja 64-bit HWND na Win64**. Pozostałe
    parametry: ``DWORD``/``UINT`` to ``c_uint`` (32-bit), ``WPARAM``/``LPARAM`` oraz
    ``pvAttribute`` są wskaźnikowo-szerokie (``c_void_p``).

    ``hwnd_type`` jest wstrzykiwany (a nie importowany z ``wintypes``), by tę logikę
    dało się przetestować poza Windows (``wintypes`` jest tam nieimportowalne).
    """
    dword = ctypes.c_uint
    ptr = ctypes.c_void_p
    dwm.DwmSetWindowAttribute.argtypes = (hwnd_type, dword, ptr, dword)
    dwm.DwmSetWindowAttribute.restype = ctypes.c_long  # HRESULT
    user32.SendMessageW.argtypes = (hwnd_type, ctypes.c_uint, ptr, ptr)
    user32.SendMessageW.restype = ptr  # LRESULT (pointer-sized)
    user32.SetWindowPos.argtypes = (
        hwnd_type,  # hWnd
        hwnd_type,  # hWndInsertAfter — też uchwyt
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        dword,  # uFlags
    )
    user32.SetWindowPos.restype = ctypes.c_int  # BOOL


def _set_titlebar_win(hwnd: int, dark: bool) -> None:
    """Windowsowa implementacja ustawienia koloru paska tytułu."""
    try:
        # wintypes jest importowalne tylko na Windows; HWND = c_void_p (pointer-sized).
        from ctypes import wintypes

        # getattr: ``ctypes.windll`` istnieje tylko na Windows (czysty mypy cross-platform).
        windll: Any = getattr(ctypes, "windll")  # noqa: B009
        dwm = windll.dwmapi
        user32 = windll.user32
        # Ustaw argtypes ZANIM przekażemy uchwyt — inaczej 64-bit HWND się utnie.
        _configure_signatures(dwm, user32, wintypes.HWND)

        value = ctypes.c_int(1 if dark else 0)
        hr = dwm.DwmSetWindowAttribute(
            hwnd, _DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value)
        )
        if hr != 0:  # starszy build Win10 — spróbuj atrybutu 19
            dwm.DwmSetWindowAttribute(
                hwnd, _DWMWA_USE_IMMERSIVE_DARK_MODE_OLD, ctypes.byref(value), ctypes.sizeof(value)
            )
        _force_frame_redraw(user32, hwnd)
    except Exception as exc:
        # Różne błędy ctypes/DWM (brak API, zły HWND) — jednolicie jako brak wsparcia.
        logger.warning("Nie udało się ustawić koloru paska tytułu: %s", exc)


def _force_frame_redraw(user32: Any, hwnd: int) -> None:
    """Wymusza przemalowanie obszaru nieklienckiego (pasek tytułu).

    Bez mrugania oknem: dezaktywacja/aktywacja paska (``WM_NCACTIVATE`` 0→1) plus
    ``SetWindowPos`` z ``SWP_FRAMECHANGED``. Naprawia sytuację, gdy na Win10
    pasek tytułu nie odświeża się po zmianie motywu. Uchwyt idzie z ustawionym
    ``argtypes`` (pointer-sized), więc nie ulega truncacji.
    """
    user32.SendMessageW(hwnd, _WM_NCACTIVATE, 0, 0)
    user32.SendMessageW(hwnd, _WM_NCACTIVATE, 1, 0)
    user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, _SWP_FRAME_REDRAW)
