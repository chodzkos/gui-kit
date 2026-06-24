"""Pole ścieżki: ``QLineEdit`` + przycisk „…" otwierający dialog wyboru.

Pierwszy wspólny widget warstwy ``qt/widgets`` (wyniesiony z EpubForge). Jest
odsprzężony od jakiejkolwiek aplikacji:

* **config** to ``DialogConfig`` (``MutableMapping[str, Any]``) — ten sam typ, co
  biorą kitowe dialogi; zwykły ``dict`` spełnia protokół;
* **i18n** jest przez parametry: teksty tooltipów i tytułów dialogów podaje się w
  :class:`PathEntryTexts` (domyślnie po angielsku) — kit nie narzuca mechanizmu
  tłumaczeń, aplikacja wstrzykuje przetłumaczone stringi.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QToolButton, QWidget

from chodzkos_gui_kit.qt.dialogs import DialogConfig, open_file, pick_dir, save_file

PathMode = Literal["dir", "file", "save"]
FileTypes = Sequence[tuple[str, str]]


@dataclass(frozen=True)
class PathEntryTexts:
    """Teksty UI :class:`PathEntry` (domyślnie po angielsku — aplikacja tłumaczy)."""

    tooltip_dir: str = "Choose folder"
    tooltip_file: str = "Choose file"
    tooltip_save: str = "Choose save location"
    title_dir: str = "Choose folder"
    title_file: str = "Choose file"
    title_save: str = "Save as"


class PathEntry(QWidget):
    """Pole tekstowe z przyciskiem wyboru ścieżki (plik/folder/zapis).

    Emituje :attr:`path_changed` przy każdej zmianie tekstu. Jeśli przekazano
    ``config`` i ``remember_key``, zapamiętuje katalog ostatniego wyboru i używa
    go jako punktu startowego kolejnego dialogu.
    """

    path_changed = Signal(str)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        mode: PathMode = "dir",
        filetypes: FileTypes | None = None,
        placeholder: str = "",
        config: DialogConfig | None = None,
        remember_key: str | None = None,
        texts: PathEntryTexts | None = None,
    ) -> None:
        super().__init__(parent)
        self.mode = mode
        self.filetypes: FileTypes = filetypes or [("All files", "*.*")]
        self._config = config
        self._remember_key = remember_key
        self._texts = texts or PathEntryTexts()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.entry = QLineEdit(self)
        if placeholder:
            self.entry.setPlaceholderText(placeholder)
        self.entry.textChanged.connect(self.path_changed.emit)
        layout.addWidget(self.entry, stretch=1)

        self.button = QToolButton(self)
        self.button.setText("…")
        self.button.setToolTip(self._browse_tooltip())
        self.button.clicked.connect(self._browse)
        layout.addWidget(self.button)

    def get(self) -> str:
        """Zwraca aktualną ścieżkę bez białych znaków na końcach."""
        return self.entry.text().strip()

    def set(self, value: str) -> None:
        """Ustawia wartość pola."""
        self.entry.setText(value)

    def _browse(self) -> None:
        """Otwiera dialog wyboru ścieżki (natywny w trybie jasnym, Qt w ciemnym)."""
        title = self._dialog_title()
        start_dir = self._start_dir()
        if self.mode == "dir":
            path = pick_dir(self, title, start_dir, self._config)
        elif self.mode == "file":
            path = open_file(self, title, start_dir, self._filter(), self._config)
        else:
            path = save_file(self, title, start_dir, self._filter(), self._config)
        if path:
            self.set(path)
            self._remember(path)

    def _filter(self) -> str:
        """Buduje string filtra Qt z listy ``(opis, wzorzec)``."""
        return ";;".join(f"{label} ({pattern})" for label, pattern in self.filetypes)

    def _start_dir(self) -> str:
        """Katalog startowy dialogu: bieżąca wartość, potem zapamiętany."""
        current = self.get()
        if current:
            path = Path(current)
            return str(path if path.is_dir() else path.parent)
        if self._config is not None and self._remember_key:
            return str(self._config.get(self._remember_key, ""))
        return ""

    def _remember(self, path: str) -> None:
        """Zapamiętuje katalog wybranej ścieżki w configu (jeśli skonfigurowano)."""
        if self._config is None or not self._remember_key:
            return
        chosen = Path(path)
        directory = chosen if chosen.is_dir() else chosen.parent
        self._config[self._remember_key] = str(directory)

    def _browse_tooltip(self) -> str:
        """Zwraca tooltip przycisku wyboru ścieżki wg trybu."""
        if self.mode == "file":
            return self._texts.tooltip_file
        if self.mode == "save":
            return self._texts.tooltip_save
        return self._texts.tooltip_dir

    def _dialog_title(self) -> str:
        """Zwraca tytuł dialogu wyboru ścieżki wg trybu."""
        if self.mode == "file":
            return self._texts.title_file
        if self.mode == "save":
            return self._texts.title_save
        return self._texts.title_dir
