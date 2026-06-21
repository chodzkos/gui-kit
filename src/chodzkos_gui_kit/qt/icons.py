"""Przebarwialne ikony SVG (Lucide) wg palety marki (GUI_STANDARD §5, §7).

Ekstrakcja sprawdzonego `IconProvider` z IcoForge. Ikony to przebarwialne SVG (a
NIE statyczne PNG): podmieniamy `currentColor` na kolor z palety, dzięki czemu
podążają za motywem. Render do `QPixmap` z obsługą HiDPI; wynik cache'owany po
`(name, hex, size)` i czyszczony przy zmianie motywu (:func:`clear_cache`).

Kolory pochodzą WYŁĄCZNIE z :mod:`chodzkos_gui_kit.palette` — token rozwiązujemy
na polu bieżącej palety (:func:`chodzkos_gui_kit.qt.theme.current_palette`).
Moduł zna PALETĘ, nie ``ThemeManager`` — brak zależności cyklicznej (``theme`` nie
importuje ``icons``).

Integracja z motywem (po stronie aplikacji): podłącz czyszczenie cache do sygnału
menedżera motywu i przerysuj ikony, np.::

    theme_manager.theme_changed.connect(icons.clear_cache)
    theme_manager.theme_changed.connect(lambda _p: button.setIcon(icons.get_icon("save")))

Reguła kontrastu (§5): ikona pełniąca rolę TEKSTU w jasnym motywie powinna używać
tokena ``"accent_text"`` (dark→accent, light→accent2), nie surowego ``"accent"``.
"""

from __future__ import annotations

from importlib.resources import files

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QGuiApplication, QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from chodzkos_gui_kit.palette import Palette
from chodzkos_gui_kit.qt.theme import current_palette

# Akcja (klucz semantyczny) → plik SVG w assets/icons. Jedyne miejsce zmiany przy
# podmianie zestawu ikon (GUI_STANDARD §5).
ICON_MAP: dict[str, str] = {
    "pencil": "pencil.svg",
    "eraser": "eraser.svg",
    "eyedropper": "pipette.svg",
    "fill": "paint-bucket.svg",
    "line": "minus.svg",
    "rectangle": "square.svg",
    "selection": "square-dashed.svg",
    "swap_colors": "arrow-left-right.svg",
    "reset_colors": "rotate-ccw.svg",
    "zoom_in": "zoom-in.svg",
    "zoom_out": "zoom-out.svg",
    "zoom_fit": "maximize.svg",
    "zoom_1to1": "scan.svg",
    "undo": "undo-2.svg",
    "redo": "redo-2.svg",
    "copy": "copy.svg",
    "cut": "scissors.svg",
    "paste": "clipboard-paste.svg",
    "save": "save.svg",
    "new_ico": "file-plus.svg",
    "open": "folder-open.svg",
}

# Domyślny token koloru (rola tekstu głównego).
_DEFAULT_TOKEN = "fg"

# Cache wyrenderowanych ikon: (nazwa, hex, rozmiar) → QIcon.
_cache: dict[tuple[str, str, int], QIcon] = {}


def get_icon(name: str, color: str | None = None, size: int = 20) -> QIcon:
    """Zwraca przebarwioną ikonę Lucide dla akcji semantycznej.

    Args:
        name: klucz z :data:`ICON_MAP`, np. ``"save"``.
        color: token palety (``"fg"``, ``"red"``, ``"amber"``, ``"accent"``,
            ``"accent_text"``…); ``None`` → ``"fg"``. Nieznany token → ``fg``.
        size: logiczny rozmiar ikony w px (render uwzględnia ``devicePixelRatio``).

    Returns:
        Wyrenderowana :class:`QIcon` albo pusta ``QIcon()`` gdy nazwa/SVG/aplikacja
        Qt są niedostępne (nigdy nie podnosi wyjątku — ikona to kosmetyka).
    """
    hex_color = _resolve_color(color or _DEFAULT_TOKEN)
    key = (name, hex_color, size)
    cached = _cache.get(key)
    if cached is not None:
        return cached

    svg_text = _load_recolored_svg(name, hex_color)
    if svg_text is None or QGuiApplication.instance() is None:
        return QIcon()

    icon = _render_icon(svg_text, size)
    if not icon.isNull():
        _cache[key] = icon
    return icon


def clear_cache() -> None:
    """Czyści cache ikon po zmianie motywu (potem konsument woła ``setIcon``)."""
    _cache.clear()


def _resolve_color(token: str, palette: Palette | None = None) -> str:
    """Rozwiązuje token na hex z bieżącej palety; nieznany token → ``fg``."""
    pal = palette if palette is not None else current_palette()
    value = getattr(pal, token, None)
    return value if isinstance(value, str) else pal.fg


def _load_recolored_svg(name: str, hex_color: str) -> str | None:
    """Wczytuje SVG akcji i podmienia ``currentColor`` na kolor (lub ``None``)."""
    svg_file = ICON_MAP.get(name)
    if svg_file is None:
        return None
    try:
        svg_text = (files("chodzkos_gui_kit") / "assets" / "icons" / svg_file).read_text(
            encoding="utf-8"
        )
    except (FileNotFoundError, OSError, ModuleNotFoundError):
        return None
    return svg_text.replace("currentColor", hex_color)


def _render_icon(svg_text: str, size: int) -> QIcon:
    """Renderuje SVG do :class:`QIcon` z obsługą HiDPI (``devicePixelRatio``)."""
    renderer = QSvgRenderer(QByteArray(svg_text.encode("utf-8")))
    if not renderer.isValid():
        return QIcon()

    screen = QGuiApplication.primaryScreen()
    dpr = screen.devicePixelRatio() if screen is not None else 1.0
    px_size = max(1, int(size * dpr))

    image = QImage(px_size, px_size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    try:
        renderer.render(painter)
    finally:
        painter.end()

    pixmap = QPixmap.fromImage(image)
    pixmap.setDevicePixelRatio(dpr)
    return QIcon(pixmap)
