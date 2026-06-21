"""Dialogi wyboru plików/folderów spójne z motywem (GUI_STANDARD §4, v2.2/2.6).

Domyślnie używamy natywnego dialogu systemu (ma pasek „Szybki dostęp" i jest
spójny, gdy motyw aplikacji == motyw systemu). Przy ROZJEŹDZIE motywów (w obie
strony) natywny dialog kłóci się z aplikacją — wtedy używamy dialogu Qt
(``DontUseNativeDialog``), ciemnimy jego pasek tytułu przez DWM i dopieszczamy
go: pasek boczny (Pulpit/Dokumenty/Pobrane/dyski/ostatni katalog), widok
szczegółowy i zapamiętany rozmiar okna.

⚠️ Pasek tytułu (DWM) trzeba pociemnić zanim okno się pokaże — tworzymy więc
natywny uchwyt (``WA_NativeWindow``) przed ``exec()``.

⚠️ Przyciski toolbara (v2.6): app-owy QSS ``QToolButton { padding/border }``
przecieka do nienatywnego dialogu i przycina przypięty ~22 px przycisk do zera
(stąd „puste, tylko tooltip"). Per-widget QSS o wyższej specyficzności zdejmuje
to przycięcie, a brakujące ikony uzupełniamy ``standardIcon``.
"""

from __future__ import annotations

import logging
from collections.abc import MutableMapping
from pathlib import Path
from typing import Any

from PySide6.QtCore import QDir, QStandardPaths, Qt, QUrl
from PySide6.QtWidgets import QFileDialog, QStyle, QToolButton, QWidget

from chodzkos_gui_kit.qt.theme import ThemeName, current_palette, mode_of, system_scheme
from chodzkos_gui_kit.qt.titlebar import sync_titlebar

logger = logging.getLogger(__name__)

# Luźny słownik konfiguracji (np. chodzkos_gui_kit.config.Config albo zwykły dict).
DialogConfig = MutableMapping[str, Any]

# Standardowe ikony przycisków nawigacji nienatywnego QFileDialog (po objectName).
_NAV_ICONS: dict[str, QStyle.StandardPixmap] = {
    "backButton": QStyle.StandardPixmap.SP_ArrowBack,
    "forwardButton": QStyle.StandardPixmap.SP_ArrowForward,
    "toParentButton": QStyle.StandardPixmap.SP_FileDialogToParent,
    "newFolderButton": QStyle.StandardPixmap.SP_FileDialogNewFolder,
}

# Diagnoza (offscreen + Windows): dialog przypina przyciski toolbara do ~22 px,
# a app-owy QSS `QToolButton { padding: 4px 12px; border: 1px }` dokłada 24 px
# poziomego paddingu — w 22 px przycisku przycina ikonę DO ZERA (stąd „puste,
# tylko tooltip"). Per-widget QSS o wyższym priorytecie zdejmuje to przycięcie,
# żeby standardowa ikona 16 px się zmieściła (tekst i tak nie wejdzie w 22 px).
_TOOLBUTTON_RESET_QSS = "QToolButton { padding: 1px; border: none; }"

# Klucz i domyślny rozmiar okna dialogu Qt (zapamiętywane w configu).
_DIALOG_SIZE_KEY = "file_dialog_size"
_DEFAULT_DIALOG_SIZE = (900, 550)
# Klucz ostatnio używanego katalogu (wspólny z polami ścieżek/eksportem).
_LAST_DIR_KEY = "last_output_dir"


def use_native_dialog(app_mode: ThemeName, system: ThemeName) -> bool:
    """Czy użyć natywnego dialogu systemu.

    Reguła symetryczna: natywny dialog (idący za motywem systemu) jest spójny
    TYLKO gdy efektywny motyw aplikacji == motyw systemu. Przy KAŻDYM rozjeździe
    (ciemny↔jasny w obie strony) używamy dialogu Qt z paskiem tytułu zgodnym z
    aplikacją. W trybie auto motywy są z definicji zgodne → zawsze natywny.
    """
    return app_mode == system


def open_file(
    parent: QWidget | None,
    title: str,
    start_dir: str,
    name_filter: str,
    config: DialogConfig | None = None,
) -> str:
    """Wybór jednego istniejącego pliku. Zwraca ścieżkę lub ``""``."""
    if _native():
        path, _ = QFileDialog.getOpenFileName(parent, title, start_dir, name_filter)
        return path
    dialog = _dark_dialog(parent, title, start_dir, config)
    dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
    _set_filters(dialog, name_filter)
    return _first_selected(dialog, config)


def open_files(
    parent: QWidget | None,
    title: str,
    name_filter: str,
    config: DialogConfig | None = None,
) -> list[str]:
    """Wybór wielu istniejących plików. Zwraca listę ścieżek (może być pusta)."""
    if _native():
        paths, _ = QFileDialog.getOpenFileNames(parent, title, "", name_filter)
        return paths
    dialog = _dark_dialog(parent, title, "", config)
    dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
    _set_filters(dialog, name_filter)
    _force_toolbar_buttons(dialog)
    accepted = dialog.exec()
    _persist_size(dialog, config)
    return dialog.selectedFiles() if accepted else []


def save_file(
    parent: QWidget | None,
    title: str,
    start_dir: str,
    name_filter: str,
    config: DialogConfig | None = None,
    *,
    initial_name: str | None = None,
) -> str:
    """Wybór miejsca i nazwy zapisu. Zwraca ścieżkę lub ``""``.

    ``initial_name`` prefilluje nazwę pliku (np. ``"rysunek.png"``). Obie gałęzie
    — natywna i fallback — dają TEN SAM efekt (prefill widoczny): natywna przez
    pełną ścieżkę w ``dir`` ``getSaveFileName``, fallback przez ``selectFile``.
    """
    if _native():
        native_dir = _with_initial_name(start_dir, initial_name)
        path, _ = QFileDialog.getSaveFileName(parent, title, native_dir, name_filter)
        return path
    dialog = _dark_dialog(parent, title, start_dir, config)
    dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
    dialog.setFileMode(QFileDialog.FileMode.AnyFile)
    _set_filters(dialog, name_filter)
    if initial_name:
        dialog.selectFile(initial_name)
    return _first_selected(dialog, config)


def _with_initial_name(start_dir: str, initial_name: str | None) -> str:
    """Łączy katalog startowy z nazwą pliku — dla prefillu natywnego ``getSaveFileName``.

    ``getSaveFileName`` traktuje ``dir`` zawierający nazwę pliku jako prefill
    (otwiera w katalogu i podstawia nazwę). Bez ``initial_name`` zwraca sam katalog.
    """
    if not initial_name:
        return start_dir
    return str(Path(start_dir) / initial_name) if start_dir else initial_name


def pick_dir(
    parent: QWidget | None,
    title: str,
    start_dir: str = "",
    config: DialogConfig | None = None,
) -> str:
    """Wybór istniejącego folderu. Zwraca ścieżkę lub ``""``."""
    if _native():
        return QFileDialog.getExistingDirectory(parent, title, start_dir)
    dialog = _dark_dialog(parent, title, start_dir, config)
    dialog.setFileMode(QFileDialog.FileMode.Directory)
    dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
    return _first_selected(dialog, config)


def _native() -> bool:
    """Decyzja natywny/Qt na podstawie bieżącego motywu i motywu systemu.

    Motyw systemu czytamy W MOMENCIE otwarcia dialogu (nie cache'ujemy ze startu).
    """
    return use_native_dialog(mode_of(current_palette()), system_scheme())


def _dark_dialog(
    parent: QWidget | None, title: str, start_dir: str, config: DialogConfig | None
) -> QFileDialog:
    """Buduje dopieszczony dialog Qt (nie-natywny) z ciemnym paskiem tytułu.

    Ustawia pasek boczny (standardowe katalogi + dyski + ostatni katalog), widok
    szczegółowy i odtwarza zapamiętany rozmiar okna.
    """
    dialog = QFileDialog(parent, title, start_dir)
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    # Wymusza utworzenie natywnego okna, by DWM pociemnił pasek przed pokazaniem.
    dialog.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
    dialog.setViewMode(QFileDialog.ViewMode.Detail)
    dialog.setSidebarUrls(_sidebar_urls(start_dir, config))
    _restore_size(dialog, config)
    # Etykiety przycisków toolbara ustawiamy DOPIERO przed exec() (_force_toolbar_buttons)
    # — tuż po konstrukcji wewnętrzne QToolButton-y bywają jeszcze nieobsadzone.
    sync_titlebar(dialog, mode_of(current_palette()))
    return dialog


def _force_toolbar_buttons(dialog: QFileDialog) -> None:
    """Przywraca widoczność przycisków toolbara nienatywnego QFileDialog (v2.6).

    Zdejmuje z KAŻDEGO ``QToolButton`` dialogu app-owy QSS (padding/border), który
    w wąskim (~22 px) przycisku przycinał ikonę do zera (back/forward/toParent/
    newFolder oraz przełączniki widoku) — zostawał sam tooltip. Przyciskom
    nawigacji dokłada standardową ikonę, gdy ich własna jest pusta. Wołane tuż
    przed ``exec()``, gdy drzewo widgetów dialogu jest już zbudowane.
    """
    buttons = dialog.findChildren(QToolButton)
    # Diagnostyka regresji „puste przyciski" — realne objectName w danej wersji Qt.
    logger.debug("QFileDialog toolbar buttons: %s", [b.objectName() for b in buttons])
    style = dialog.style()
    for button in buttons:
        button.setStyleSheet(_TOOLBUTTON_RESET_QSS)
        pixmap = _NAV_ICONS.get(button.objectName())
        if pixmap is not None and button.icon().isNull():
            button.setIcon(style.standardIcon(pixmap))


def _sidebar_urls(start_dir: str, config: DialogConfig | None) -> list[QUrl]:
    """Buduje pasek boczny: Pulpit, Dokumenty, Pobrane, dyski, ostatni katalog."""
    urls: list[QUrl] = []
    for location in (
        QStandardPaths.StandardLocation.DesktopLocation,
        QStandardPaths.StandardLocation.DocumentsLocation,
        QStandardPaths.StandardLocation.DownloadLocation,
    ):
        paths = QStandardPaths.standardLocations(location)
        if paths:
            urls.append(QUrl.fromLocalFile(paths[0]))
    for drive in QDir.drives():
        urls.append(QUrl.fromLocalFile(drive.absoluteFilePath()))
    last = _last_dir(start_dir, config)
    if last:
        urls.append(QUrl.fromLocalFile(last))

    # Deduplikacja z zachowaniem kolejności (różne lokalizacje bywają tym samym).
    seen: set[str] = set()
    unique: list[QUrl] = []
    for url in urls:
        key = url.toString()
        if key and key not in seen:
            seen.add(key)
            unique.append(url)
    return unique


def _last_dir(start_dir: str, config: DialogConfig | None) -> str:
    """Ostatni używany katalog: bieżący punkt startowy albo zapamiętany w configu."""
    if start_dir and Path(start_dir).is_dir():
        return start_dir
    if config is not None:
        value = config.get(_LAST_DIR_KEY)
        if isinstance(value, str) and value:
            return value
    return ""


def _restore_size(dialog: QFileDialog, config: DialogConfig | None) -> None:
    """Odtwarza rozmiar okna z configu albo ustawia domyślny."""
    width, height = _DEFAULT_DIALOG_SIZE
    if config is not None:
        saved = config.get(_DIALOG_SIZE_KEY)
        if (
            isinstance(saved, (list, tuple))
            and len(saved) == 2
            and all(isinstance(value, int) for value in saved)
        ):
            width, height = saved[0], saved[1]
    dialog.resize(width, height)


def _persist_size(dialog: QFileDialog, config: DialogConfig | None) -> None:
    """Zapisuje rozmiar okna do configu (``Config.__setitem__`` = mark_dirty)."""
    if config is not None:
        size = dialog.size()
        config[_DIALOG_SIZE_KEY] = [size.width(), size.height()]


def _set_filters(dialog: QFileDialog, name_filter: str) -> None:
    """Ustawia filtry nazw, rozbijając łańcuch Qt rozdzielany ``;;``."""
    parts = [part for part in name_filter.split(";;") if part]
    if parts:
        dialog.setNameFilters(parts)


def _first_selected(dialog: QFileDialog, config: DialogConfig | None) -> str:
    """Wykonuje dialog, zapamiętuje rozmiar i zwraca pierwszą ścieżkę lub ``""``."""
    _force_toolbar_buttons(dialog)
    accepted = dialog.exec()
    _persist_size(dialog, config)
    if accepted:
        files = dialog.selectedFiles()
        return files[0] if files else ""
    return ""
