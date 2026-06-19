"""Paleta marki — JEDYNE miejsce z hexami w całym kicie.

Źródło: GUI_STANDARD.md §5 (paleta + stany pochodne).
Czysty Python, zero zależności — czytają stąd: generator QSS (qt/theme.py),
słownik tkinter (tk/theme.py), w przyszłości eksport tokenów dla Fluttera.

Reguła kontrastu: w jasnym motywie kolor TEKSTU/LINKU akcentowego to
`accent2` (#0F7C5B, >=4.5:1 na białym); `accent` służy wypełnieniom i ikonom.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    """Komplet kolorów motywu wraz ze stanami pochodnymi (GUI_STANDARD §5)."""

    name: str  # "dark" | "light"

    # — baza —
    bg: str  # tło główne
    bg2: str  # tło sekcji / paneli
    bg3: str  # tło pól / inputów
    fg: str  # tekst główny
    fg2: str  # tekst drugorzędny
    fg3: str  # tekst wyciszony / hinty
    accent: str  # akcent marki (wypełnienia, ikony)
    accent2: str  # akcent ciemniejszy (przyciski; w light: tekst/linki!)
    border: str  # ramki / separatory
    red: str  # błędy / akcje destrukcyjne
    amber: str  # ostrzeżenia

    # — stany pochodne (obowiązkowe wg §5) —
    hover: str
    pressed: str
    selection_bg: str
    selection_fg: str
    disabled_fg: str
    disabled_bg: str
    placeholder: str
    focus_border: str

    @property
    def is_dark(self) -> bool:
        return self.name == "dark"

    @property
    def accent_text(self) -> str:
        """Kolor akcentowy bezpieczny dla TEKSTU (reguła kontrastu §5)."""
        return self.accent if self.is_dark else self.accent2


DARK = Palette(
    name="dark",
    bg="#1e2028",
    bg2="#252830",
    bg3="#2d3040",
    fg="#dde1ec",
    fg2="#8b90a7",
    fg3="#555a70",
    accent="#5DCAA5",
    accent2="#1D9E75",
    border="#383c50",
    red="#e25454",
    amber="#EF9F27",
    hover="#383c50",
    pressed="#262936",
    selection_bg="#1D9E75",
    selection_fg="#ffffff",
    disabled_fg="#555a70",
    disabled_bg="#252830",
    placeholder="#555a70",
    focus_border="#5DCAA5",
)

LIGHT = Palette(
    name="light",
    bg="#ffffff",
    bg2="#f5f5f7",
    bg3="#e8e8ed",
    fg="#1d1d1f",
    fg2="#515154",
    fg3="#86868b",
    accent="#1D9E75",
    accent2="#0F7C5B",
    border="#d1d1d6",
    red="#d70015",
    amber="#b25000",
    hover="#dcdce2",
    pressed="#d4d4da",
    selection_bg="#0F7C5B",
    selection_fg="#ffffff",
    disabled_fg="#86868b",
    disabled_bg="#f5f5f7",
    placeholder="#86868b",
    focus_border="#1D9E75",
)

PALETTES: dict[str, Palette] = {"dark": DARK, "light": LIGHT}


def get(name: str) -> Palette:
    """Zwraca paletę po nazwie; nieznana nazwa → dark (spójnie z regułą Unknown→dark)."""
    return PALETTES.get(name, DARK)
