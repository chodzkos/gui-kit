"""Lista plików z toolbarem i natywnym drag&drop (Qt).

Wyniesiona z EpubForge i odsprzężona od aplikacji (config → ``DialogConfig``,
i18n → parametry tekstowe + wstrzykiwany ``count_label``).

Układ pod przyszły ``UrlList`` (ten sam szkielet, inne wejście). Świadomie
rozdzielone:

* **szkielet wizualny** — toolbar (przyciski + licznik) i lista (``QListWidget``
  + sygnały ``files_changed``/``selection_changed`` + zaznaczenie): metody
  ``_build_*``, ``_refresh``, ``current_path``, ``select_first``, ``clear``,
  ``_remove_selected``; nie wie nic o rozszerzeniach ani o ``Path``;
* **logika wejścia (PLIKI)** — co jest prawidłowym elementem i jak go dodać:
  ``_accepts``, ``_normalize``, ``add_files``, ``_expand_drop``, ``_add_files``,
  ``_add_folder``. To jedyna część, którą ``UrlList`` podmieni (str/QUrl, walidacja
  schematu, wklejanie z clipboardu).

Bazy abstrakcyjnej NIE wydzielamy — dopóki nie ma drugiego konsumenta szkieletu
byłaby spekulacją. Ten podział ma sprawić, że późniejsze wydzielenie będzie
mechaniczne, nie przepisaniem.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from chodzkos_gui_kit.qt.dialogs import DialogConfig, open_files, pick_dir


@dataclass(frozen=True)
class FileListTexts:
    """Teksty UI :class:`FileList` (domyślnie po angielsku — aplikacja tłumaczy)."""

    files: str = "Files"
    folder: str = "Folder"
    remove: str = "Remove"
    clear: str = "Clear"
    tooltip_files: str = "Add files via a dialog"
    tooltip_folder: str = "Add supported files from a folder"
    tooltip_remove: str = "Remove selected items from the list"
    tooltip_clear: str = "Remove all items from the list"
    list_tooltip: str = "File list — drag files here or use the buttons above"
    dialog_add_files: str = "Add files"
    dialog_add_folder: str = "Add folder"
    # MUSI zawierać „{pattern}" — podstawiamy listę masek rozszerzeń.
    filter_supported: str = "Supported ({pattern})"


def _default_count_label(count: int) -> str:
    """Domyślny licznik (ang., bez form mnogich) — aplikacja wstrzykuje ngettext."""
    return f"{count} files"


class FileList(QWidget):
    """Lista plików z przyciskami dodawania, usuwania i czyszczenia.

    Drag&drop jest natywny (Qt): upuszczenie plików dodaje pasujące rozszerzenia,
    a upuszczenie folderu skanuje go rekurencyjnie. Bez ``extensions`` lista
    akceptuje wszystkie pliki.

    Sygnały:
        files_changed: lista plików zmieniła się (niesie kopię ``list[Path]``).
        selection_changed: zmieniono zaznaczenie (niesie ``Path`` lub ``None``).

    Args:
        extensions: akceptowane rozszerzenia (z kropką, dowolna wielkość liter);
            ``None`` → akceptuj wszystkie pliki.
        confirm: hook wołany przed dodaniem pliku — ``False`` pomija plik.
        config: ``DialogConfig`` dla dopieszczonego dialogu Qt (pasek boczny, rozmiar).
        texts: etykiety UI (domyślnie ang.).
        count_label: funkcja ``liczba → tekst licznika`` (wstrzyknij ngettext).
    """

    files_changed = Signal(list)
    selection_changed = Signal(object)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        extensions: Iterable[str] | None = None,
        confirm: Callable[[Path], bool] | None = None,
        config: DialogConfig | None = None,
        texts: FileListTexts | None = None,
        count_label: Callable[[int], str] | None = None,
    ) -> None:
        super().__init__(parent)
        self.extensions: set[str] | None = (
            {ext.lower() for ext in extensions} if extensions is not None else None
        )
        self.confirm = confirm
        self._config = config
        self._texts = texts or FileListTexts()
        self._count_label = count_label or _default_count_label
        self._files: list[Path] = []

        self._build_ui()
        self.setAcceptDrops(True)

    # ── Szkielet wizualny (toolbar + lista + sygnały) ──────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addLayout(self._build_toolbar())

        self.listbox = QListWidget(self)
        self.listbox.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.listbox.setToolTip(self._texts.list_tooltip)
        self.listbox.currentRowChanged.connect(self._on_current_row_changed)
        layout.addWidget(self.listbox, stretch=1)

    def _build_toolbar(self) -> QHBoxLayout:
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)
        self._add_files_btn = self._make_button("+ " + self._texts.files, self._texts.tooltip_files)
        self._add_files_btn.clicked.connect(self._add_files)
        self._add_folder_btn = self._make_button(
            "+ " + self._texts.folder, self._texts.tooltip_folder
        )
        self._add_folder_btn.clicked.connect(self._add_folder)
        self._remove_btn = self._make_button(self._texts.remove, self._texts.tooltip_remove)
        self._remove_btn.clicked.connect(self._remove_selected)
        self._clear_btn = self._make_button(self._texts.clear, self._texts.tooltip_clear)
        self._clear_btn.clicked.connect(self.clear)
        toolbar.addWidget(self._add_files_btn)
        toolbar.addWidget(self._add_folder_btn)
        toolbar.addWidget(self._remove_btn)
        toolbar.addWidget(self._clear_btn)
        toolbar.addStretch(1)
        self.count_label = QLabel(self._count_label(0))
        toolbar.addWidget(self.count_label)
        return toolbar

    def _make_button(self, text: str, tooltip: str) -> QPushButton:
        button = QPushButton(text, self)
        button.setToolTip(tooltip)
        return button

    def _refresh(self) -> None:
        """Odświeża widok listy i licznik, emituje ``files_changed``."""
        self.listbox.clear()
        for path in self._files:
            QListWidgetItem(f"{path.name}  ({path.parent})", self.listbox)
        self.count_label.setText(self._count_label(len(self._files)))
        self.files_changed.emit(self.files())

    def _on_current_row_changed(self, _row: int) -> None:
        self.selection_changed.emit(self.current_path())

    def _remove_selected(self) -> None:
        """Usuwa zaznaczone pozycje (operacja na szkielecie, niezależna od typu)."""
        rows = sorted((index.row() for index in self.listbox.selectedIndexes()), reverse=True)
        if not rows:
            return
        for row in rows:
            self._files.pop(row)
        self._refresh()

    # ── API publiczne ──────────────────────────────────────────────────────────

    def files(self) -> list[Path]:
        """Zwraca kopię listy plików."""
        return list(self._files)

    def clear(self) -> None:
        """Czyści listę plików."""
        if not self._files:
            return
        self._files.clear()
        self._refresh()

    def current_path(self) -> Path | None:
        """Zwraca aktualnie zaznaczony plik (lub ``None``)."""
        row = self.listbox.currentRow()
        if 0 <= row < len(self._files):
            return self._files[row]
        return None

    def select_first(self) -> None:
        """Zaznacza pierwszy plik na liście, jeśli istnieje."""
        if self._files:
            self.listbox.setCurrentRow(0)

    # ── Logika wejścia (PLIKI) — część podmieniana przez przyszły UrlList ──────

    def add_files(self, paths: Iterable[str | Path]) -> None:
        """Dodaje pozycje spełniające filtr rozszerzeń (z dedupem i ``confirm``).

        Przyjmuje ``str`` lub ``Path`` — normalizuje do ``Path``, więc godzi
        konsumentów operujących na łańcuchach (pdf2md) i na ścieżkach (EpubForge).
        """
        changed = False
        for entry in paths:
            candidate = self._normalize(entry)
            if not self._accepts(candidate):
                continue
            if candidate in self._files:
                continue
            if self.confirm is not None and not self.confirm(candidate):
                continue
            self._files.append(candidate)
            changed = True
        if changed:
            self._refresh()

    def _normalize(self, entry: str | Path) -> Path:
        """Normalizuje element wejścia do ``Path`` (UrlList podmieni na str/QUrl)."""
        return Path(entry)

    def _accepts(self, path: Path) -> bool:
        """Czy element jest prawidłowy (filtr rozszerzeń; ``None`` → wszystko)."""
        if self.extensions is None:
            return True
        return path.suffix.lower() in self.extensions

    def _expand_drop(self, path: Path) -> Iterable[Path]:
        """Rozwija upuszczony element: folder → pliki rekurencyjnie, plik → on sam."""
        if path.is_dir():
            return (p for p in path.rglob("*") if p.is_file())
        return (path,)

    def _add_files(self) -> None:
        """Dodaje pliki wybrane w dialogu."""
        paths = open_files(self, self._texts.dialog_add_files, self._dialog_filter(), self._config)
        self.add_files(paths)

    def _add_folder(self) -> None:
        """Dodaje obsługiwane pliki z wybranego katalogu (bez rekursji)."""
        folder = pick_dir(self, self._texts.dialog_add_folder, "", self._config)
        if not folder:
            return
        self.add_files(path for path in Path(folder).iterdir() if path.is_file())

    def _dialog_filter(self) -> str:
        """Buduje filtr dialogu z akceptowanych rozszerzeń (``*`` gdy brak filtra)."""
        pattern = " ".join(f"*{ext}" for ext in sorted(self.extensions)) if self.extensions else "*"
        return self._texts.filter_supported.format(pattern=pattern)

    # ── Drag & drop ─────────────────────────────────────────────────────────--

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802 — Qt API
        """Akceptuje przeciąganie, gdy niesie URL-e plików/folderów."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802 — Qt API
        """Dodaje upuszczone pliki; foldery skanuje rekurencyjnie."""
        paths: list[Path] = []
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if not local:
                continue
            paths.extend(self._expand_drop(Path(local)))
        self.add_files(paths)
        event.acceptProposedAction()
