# Changelog

## [Unreleased]
### Added
- szkielet repo: palette.py (paleta + stany z GUI_STANDARD §5), pyproject z extras, CI, dokumentacja (README, ROADMAP, PROMPTS, CLAUDE.md), GUI_STANDARD.md v2.7
- ekstrakcja rdzenia Qt z EpubForge (PROMPTS P1):
  - `winutil/dwm.py` — `set_titlebar(hwnd, dark)`: czysty ctypes (DwmSetWindowAttribute 20/19, WM_NCACTIVATE 0→1, SetWindowPos FRAMECHANGED), zero Qt/tk, no-op poza Windows
  - `config.py` — generyczny `Config(app_name)` (platformdirs, zapis atomowy tmp+replace, `get`/`set`/`mark_dirty`/`flush`, hak `on_dirty` pod debounce, wariant portable)
  - `qt/theme.py` — `ThemeManager`: Fusion przed setPalette, paleta i `build_qss` z `palette.py` (zero lokalnych hexów), kanoniczna sekwencja `apply()` (v2.3), auto przez `colorScheme()` (Unknown→dark), `attach_titlebar`
  - `qt/titlebar.py` — `sync_titlebar`/`TitlebarSync`: DWM = motyw app BEZWARUNKOWO (v2.5), re-aplikacja przy Show/ActivationChange
  - `qt/dialogs.py` — natywny ⇔ zgodność motywów (symetrycznie, v2.2); fallback QFileDialog (sidebar, Detail, rozmiar z config, fix przycisków toolbara v2.6)
  - testy `pytest-qt` (offscreen) dla theme/titlebar/dialogs + testy `config` bez PySide6; testy DWM przygotowane pod marker `windows`
