"""Trwałość konfiguracji aplikacji (``config.json``) — generyczna, bez Qt.

Warstwa 0 kitu (czysty Python + ``platformdirs``): przechowuje ustawienia
aplikacji desktopowej wg GUI_STANDARD §8. Lokalizację liczy jedna funkcja
:func:`config_dir` (źródło prawdy):

* zwykła instalacja → ``platformdirs.user_config_dir(app_name, ...)``
  (``%APPDATA%\\<app>`` na Windows, ``~/.config/<app>`` na Linux,
  ``~/Library/Application Support/<app>`` na macOS);
* wariant portable (zamrożony ``.exe`` z plikiem-markerem ``portable.flag``
  obok) → config obok ``.exe``.

Zapis jest atomowy (plik tymczasowy + ``os.replace``). :class:`Config` jest
podtypem ``dict``, więc pasuje wszędzie, gdzie oczekiwany jest zwykły słownik
(np. helpery dialogów), a przy tym dokłada ``mark_dirty``/``flush`` i hak
``on_dirty`` pod debounce. Sam timer debounce żyje w GUI (np. ``QTimer``) — ten
moduł nie zna Qt, trzyma tylko zwykły ``Callable``.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import platformdirs

logger = logging.getLogger(__name__)

# Marker wariantu portable — obecność tego pliku obok exe przełącza config
# z lokalizacji systemowej na katalog obok exe (build portable go tworzy).
PORTABLE_MARKER = "portable.flag"


def _is_frozen() -> bool:
    """Czy działamy jako zamrożony ``.exe`` (PyInstaller)."""
    return bool(getattr(sys, "frozen", False))


def _exe_dir() -> Path:
    """Katalog pliku wykonywalnego (sensowny tylko w trybie frozen)."""
    return Path(sys.executable).parent


def _is_portable() -> bool:
    """Tryb portable: zamrożony exe z markerem ``portable.flag`` obok."""
    return _is_frozen() and (_exe_dir() / PORTABLE_MARKER).is_file()


def config_dir(app_name: str) -> Path:
    """Zwraca katalog konfiguracji aplikacji — jedyne źródło prawdy o lokalizacji.

    * portable (frozen + marker) → katalog obok ``.exe``;
    * w pozostałych przypadkach → ``platformdirs.user_config_dir`` z
      ``appauthor=False`` (bez zdublowanego katalogu autora) i ``roaming=True``
      (Roaming na Windows).
    """
    if _is_portable():
        return _exe_dir()
    return Path(platformdirs.user_config_dir(app_name, appauthor=False, roaming=True))


def load_config(path: Path) -> dict[str, Any]:
    """Wczytuje konfigurację z pliku JSON.

    Returns:
        Słownik konfiguracji; pusty słownik gdy plik nie istnieje albo jest
        uszkodzony (brak wyjątku — to nie jest sytuacja krytyczna).
    """
    if not path.is_file():
        return {}
    try:
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def save_config(path: Path, data: dict[str, Any]) -> None:
    """Zapisuje konfigurację do pliku JSON w sposób atomowy.

    Tworzy brakujące katalogi nadrzędne. Zapis idzie najpierw do pliku ``.tmp``,
    a następnie :func:`os.replace` podmienia plik docelowy.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


class Config(dict[str, Any]):
    """Konfiguracja aplikacji jako słownik z flagą „brudne" i atomowym zapisem.

    Jest podtypem :class:`dict`, więc pasuje wszędzie, gdzie oczekiwany jest
    zwykły słownik (helpery dialogów zapisują przez ``config[key] = ...`` i to
    automatycznie oznacza stan jako brudny). Dodatkowo wystawia generyczne
    ``get``/:meth:`set`/:meth:`mark_dirty` z kontraktu kitu.

    Debounce (odroczony zapis) realizuje GUI: ustawia ``on_dirty`` na callback
    restartujący np. ``QTimer``, który po ~1 s woła :meth:`flush`.

    Args:
        app_name: nazwa aplikacji dla ``platformdirs`` (pomijana, gdy podasz ``path``).
        path: jawna ścieżka pliku (głównie testy); domyślnie
            ``config_dir(app_name) / "config.json"``.
        on_dirty: callback wołany przy każdym oznaczeniu zmian (hak debounce).
    """

    def __init__(
        self,
        app_name: str,
        *,
        path: Path | None = None,
        on_dirty: Callable[[], None] | None = None,
    ) -> None:
        self.app_name = app_name
        self.path = path if path is not None else config_dir(app_name) / "config.json"
        # init dict nie woła __setitem__ → start „czysty".
        super().__init__(load_config(self.path))
        self.on_dirty = on_dirty
        self._dirty = False

    def set(self, key: str, value: Any) -> None:
        """Ustawia klucz i oznacza stan jako brudny (alias na ``config[key] = value``)."""
        self[key] = value

    def __setitem__(self, key: str, value: Any) -> None:
        """Zapis klucza oznacza stan jako brudny (i odpala ``on_dirty``)."""
        super().__setitem__(key, value)
        self.mark_dirty()

    @property
    def dirty(self) -> bool:
        """Czy są niezapisane zmiany."""
        return self._dirty

    def mark_dirty(self) -> None:
        """Oznacza niezapisane zmiany i powiadamia ``on_dirty`` (jeśli ustawiony)."""
        self._dirty = True
        if self.on_dirty is not None:
            self.on_dirty()

    def flush(self) -> None:
        """Zapisuje na dysk TYLKO gdy są niezapisane zmiany (cel timera debounce)."""
        if self._dirty:
            self.save_now()

    def save_now(self) -> None:
        """Zapisuje na dysk bezwarunkowo i czyści flagę (CLI / zamknięcie okna)."""
        save_config(self.path, dict(self))
        self._dirty = False
