"""Testy warstwy DWM (winutil) — marshaling uchwytu (regresja truncacji 64-bit HWND).

``winutil.dwm`` nie zależy od Qt; testy logiki marshalingu lecą na CI (ubuntu)
bez Windows. Realny efekt DWM → ``@pytest.mark.windows``.
"""

from __future__ import annotations

import ctypes
from types import SimpleNamespace

import pytest

from chodzkos_gui_kit.winutil import dwm


def test_set_titlebar_is_noop_off_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    """Poza Windows ``set_titlebar`` nie wchodzi w ścieżkę WinAPI (czysty no-op)."""
    monkeypatch.setattr(dwm.sys, "platform", "linux")
    called: list[tuple[int, bool]] = []
    monkeypatch.setattr(dwm, "_set_titlebar_win", lambda h, d: called.append((h, d)))
    # Duży, „64-bitowy" uchwyt — i tak nie powinien tknąć WinAPI poza Windows.
    dwm.set_titlebar(0x1_FFFF_FFFF, True)
    assert called == []


def test_configure_signatures_uses_pointer_sized_handle() -> None:
    """argtypes mają uchwyt jako typ WSKAŹNIKOWY — łapie regresję truncacji 64-bit HWND.

    Wstrzykujemy ``c_void_p`` (na Windows ``wintypes.HWND`` jest mu równe), dzięki
    czemu test działa bez Windows i bez ``ctypes.wintypes``.
    """
    dwm_lib = SimpleNamespace(DwmSetWindowAttribute=SimpleNamespace())
    user32 = SimpleNamespace(
        SendMessageW=SimpleNamespace(),
        SetWindowPos=SimpleNamespace(),
        RedrawWindow=SimpleNamespace(),
    )

    dwm._configure_signatures(dwm_lib, user32, ctypes.c_void_p)

    # DwmSetWindowAttribute(HWND, DWORD, LPCVOID, DWORD) → HRESULT
    assert dwm_lib.DwmSetWindowAttribute.argtypes is not None
    assert dwm_lib.DwmSetWindowAttribute.argtypes[0] is ctypes.c_void_p
    assert dwm_lib.DwmSetWindowAttribute.restype is ctypes.c_long
    # Każdy parametr-uchwyt jest wskaźnikowy (nie goły c_int).
    assert user32.SendMessageW.argtypes[0] is ctypes.c_void_p
    assert user32.SetWindowPos.argtypes[0] is ctypes.c_void_p
    assert user32.SetWindowPos.argtypes[1] is ctypes.c_void_p  # hWndInsertAfter też uchwyt
    assert user32.RedrawWindow.argtypes[0] is ctypes.c_void_p  # repaint ramki (§4)


@pytest.mark.windows
def test_real_dwm_sets_wintypes_hwnd_argtypes() -> None:
    """Na Windows realne wywołanie ustawia ``wintypes.HWND`` jako typ uchwytu."""
    from ctypes import wintypes

    dwm.set_titlebar(0, True)  # 0 = brak okna; argtypes ustawiane przed (nieudanym) wywołaniem
    windll = ctypes.windll  # type: ignore[attr-defined]
    assert windll.dwmapi.DwmSetWindowAttribute.argtypes[0] is wintypes.HWND
