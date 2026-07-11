# Changelog

## [Unreleased]

## [0.5.1]
### Fixed
- **`release` — jedno źródło prawdy o wersji przez `importlib.metadata`**: `pyproject.toml` ma statyczne `version = "0.5.1"` (usunięte `dynamic`/`[tool.hatch.version]`), a `src/chodzkos_gui_kit/__init__.py` czyta `__version__ = version("chodzkos-gui-kit")` z metadanych zainstalowanego pakietu (fallback `0.0.0+unknown` przy pracy z drzewa źródeł). Koniec z literałem w kodzie i rozjazdem (tag `v0.5.0` wiózł `__version__ = "0.4.3"`). Test strażniczy `tests/test_version.py` pilnuje zgodności z metadanymi. Zastępuje mechanizm dynamic-hatch z 0.5.0.
- **`config.load_config` — kopia uszkodzonego `config.json` zamiast cichego `{}`**: przy `JSONDecodeError` plik jest najpierw przenoszony (`os.replace`, atomowo) na `config.json.broken-<ts>` (ts z `time.strftime`, bez nadpisywania — kolejne awarie = kolejne kopie), z `logger.warning("Uszkodzony config.json — zachowano kopię %s, start z domyślnych")`, dopiero potem zwracany `{}`. Użytkownik nie traci po cichu preferencji, a kopię można zdiagnozować/odzyskać. `OSError` (nieczytelny plik) dalej daje `{}` bez ruszania pliku.
- **`tk/titlebar` — pointer-sized ctypes dla `GetParent`** (`_window_hwnd`): sygnatury ustawiane przez wydzielony `_configure_getparent` (na wzór `dwm._configure_signatures`) — `GetParent.argtypes = (wintypes.HWND,)`, `restype = wintypes.HWND`. Bez tego goły Python int marshaluje się jako 32-bit `c_int` i **truncuje 64-bit HWND na Win64**, a domyślny `restype=c_int` zwraca uchwyt z bitem 31 jako liczbę ujemną (GUI_STANDARD §4 v2.9). Wynik (`HWND`) konwertowany do `int`, `NULL → None`; `wintypes` importowany lokalnie tylko na Windows (moduł nadal importuje się na innych platformach), obsługa wyjątków i `update_idletasks` bez zmian. Publiczne API bez zmian.
- **`qt/widgets/help_html` — escaping granicy zaufania** (treść trafia surowo do `QTextBrowser.setHtml`): helpery TREŚCI `code`/`preformatted` oraz nagłówki i komórki `table` escapują wejście przez `html.escape` (`quote=False`), więc `code("a < b & c")`, listingi z przekierowaniami powłoki (`>`/`<`) i dane tabel renderują się dosłownie zamiast być interpretowane jako znaczniki. Helpery STRUKTURY `section`/`paragraph`/`unordered_list` pozostają punktami składania (HTML zaufany/zescapowany) — udokumentowane w docstringach modułu i funkcji wraz z przykładem `html.escape` po stronie konsumenta. **Zmiana zachowania**: konsument, który wcześniej wstrzykiwał HTML do `code`/`preformatted`/komórek `table`, dostanie teraz treść zescapowaną (dosłowną); do zagnieżdżania używaj helperów struktury. Publiczne sygnatury bez zmian.

## [0.5.0]
### Added
- **`qt/widgets/HelpWindow`** — okno pomocy z zakładkami (wyniesione z pdf2md). API: `HelpWindow(parent=None, *, title="Help", tabs=None)`, gdzie `tabs: list[tuple[str, str]]` to `(tytuł, html)` **wstrzykiwane w pętli** (bez sztywnych `_make_X_tab`). **Re-render przy zmianie motywu**: `changeEvent` na `PaletteChange` woła `setHtml` PONOWNIE z tym samym html — `QTextBrowser` rozwiązuje `palette(...)` do konkretnych kolorów przy każdym `setHtml`, więc statyczna lista `tabs` wystarcza (factory zbędne). Belka tytułu przez kitowy `TitlebarSync` (motyw leniwie z `current_palette`); `resize(720, 560)` bez persystencji geometrii; przycisk „Close" przez `QDialogButtonBox` (i18n Qt). **Bez parametrów i18n poza `title`** — treść to parametr.
- **`qt/widgets/help_html`** — helpery składania treści pomocy jako HTML motyw-świadomy: `section`/`paragraph`/`unordered_list`/`table`/`code`/`preformatted`. Kolory powierzchni WYŁĄCZNIE przez `palette(alternate-base)` (tło) + `palette(text)` (tekst) — zero hexów, czytelne w obu motywach po re-renderze. Reeksport w `qt/widgets/__init__`.

## [0.4.3]
### Fixed
- **Przemalowanie ramki na Win11** (`winutil/dwm.py`): w `_RDW_FRAME_REPAINT` zamieniono `RDW_NOCHILDREN` (0x0040) na `RDW_ALLCHILDREN` (0x0080) i dodano `RDW_ERASE` (0x0004), aby obejmować dzieci obszaru nieklienckiego. Win10 działał wcześniej i działa nadal.

### Changed
- **Udokumentowana granica Win11: przyciski ramki aktywnego okna** (`GUI_STANDARD §4 → v2.12`): po zmianie motywu w locie przyciski systemowe (min/max/close) **aktywnego** okna zostają w starym kolorze do FIZYCZNEGO zdarzenia stanu (minimalizacja/przykrycie/dialog) — Win11 ignoruje programowe `WM_NCACTIVATE`+`RedrawWindow` na oknie pozostającym aktywnym. To granica, nie usterka (przyciski działają, wracają przy interakcji). Sprawdzone i nieskuteczne: `RDW_ALLCHILDREN` (zostawione — nieszkodliwe, może pomagać na Win10/innych buildach) oraz odroczenie przez `QTimer.singleShot` — **cofnięte** (komplikowało kod bez efektu). Trzecia z rodziny „Win11 maluje ramkę po swojemu" (obok aktywnego resize i okien w tle).

## [0.4.2]
### Added
- **`qt/widgets/LogView`** — kolorowany log read-only (`QPlainTextEdit`), łączący wzorce EpubForge + pdf2md. `append_line(text, level)` (`QTextCharFormat`, bez HTML), limit `_MAX_BLOCKS=5000`, mono Consolas. **5 poziomów** mapowanych na role palety: `ok→accent`, `warn→amber`, `err→red`, `cmd→fg3`, `info→fg2`, nieznany→`fg`. **Re-render historii**: bufor wpisów + `set_theme(palette)` przemalowuje CAŁĄ historię (nie tylko nowe linie) — poprawność przy zmianie motywu. Wrappery zgodności `log_info`/`log_warning`/`log_error` (uwaga: `log_info → "ok"`, czyli akcent, nie wyszarzony `info`). `timestamps: bool=False` (prefiks `[HH:MM:SS]`). **Rozszerzalne poziomy** przez `level_colors: dict[str, str]` (nazwa roli palety — przeżywa zmianę motywu — albo gotowy kolor), bez zmiany kitu. Bez i18n (widget pokazuje tylko logi aplikacji).

## [0.4.1]
### Added
- **`qt/widgets/FileList`** — lista plików z toolbarem i natywnym drag&drop (wyniesiona z EpubForge). API: `files()`/`add_files()`/`clear()`/`current_path()`/`select_first()`, sygnały `files_changed`/`selection_changed`, toolbar +Files/+Folder/Remove/Clear, D&D z rekursją folderów (`rglob`), licznik. **Odsprzężony**: `config` to `DialogConfig`; i18n przez `FileListTexts` (frozen dataclass, ang. domyślne); licznik przez wstrzykiwany `count_label: Callable[[int], str]` (aplikacja podaje `ngettext` — kit bez gettext); `extensions: Iterable[str] | None` (brak → akceptuj wszystko); `confirm` hook zachowany. **`add_files` przyjmuje `str | Path`** i normalizuje do `Path`, `files()` zwraca `list[Path]` — godzi konsumentów na łańcuchach (pdf2md) i ścieżkach (EpubForge). Ułożony pod przyszły `UrlList`: szkielet wizualny (toolbar+lista+sygnały) oddzielony od logiki wejścia (filtr ext, rekursja, normalizacja) — bez przedwczesnej bazy abstrakcyjnej.

## [0.4.0]
### Added
- **`qt/widgets/PathEntry`** — pierwszy wspólny widget warstwy `qt/widgets` (wyniesiony z EpubForge). Pole `QLineEdit` + przycisk „…" otwierający kitowy dialog wg trybu (`mode` dir/file/save). API: `get()`/`set()`, sygnał `path_changed`, `filetypes`, `placeholder`, `config` + `remember_key` (zapamiętuje katalog ostatniego wyboru i startuje z niego). **Odsprzężony od aplikacji**: `config` to `DialogConfig` (`MutableMapping[str, Any]`, jak kitowe dialogi — `dict` wystarcza), a i18n jest przez parametry — teksty tooltipów/tytułów podaje `PathEntryTexts` (frozen dataclass, domyślne po angielsku; aplikacja wstrzykuje tłumaczenia). Kit nie zależy od żadnej aplikacji ani od gettext.

### Docs
- **GUI_STANDARD §4 → v2.11** (docs-only): dwie pułapki belki/DWM wyniesione na osobne punkty — (a) **`RedrawWindow(RDW_FRAME | RDW_INVALIDATE | RDW_UPDATENOW)` PO `WM_NCACTIVATE`+`SetWindowPos`** (Win10 zostawia jasne tło pod tytułem po zmianie motywu; w sekwencji DWM zostaje tylko odnośnik); (b) **belka jaśnieje podczas aktywnego resize** po zmianie motywu — granica nie do wyeliminowania bez migotania, synchronizuj PO zakończeniu ruchu (debounce ~120 ms / `WM_EXITSIZEMOVE`), nie w każdym `resizeEvent`; przy starcie w docelowym motywie nie występuje.

## [0.3.4]
### Fixed
- **`_repolish` repaintuje item-views** (`qt/theme.py`): po zmianie motywu wymusza `setPalette(app.palette())` + `viewport().update()` na `QAbstractItemView` (`QTableWidget`/`QTreeView`…). Naprawia stary ciemny `Base` po `dark→light` (Qt nie czyści per-widget resolve mask). **Celowane na item-views** (nie globalnie); flaga `apply_theme(..., repaint_item_views=True)` pozwala wyłączyć. GUI_STANDARD §4 v2.10.

### Added
- **`save_file(initial_name=…)`** (`qt/dialogs.py`): prefill nazwy zapisywanego pliku, **symetrycznie** w obu gałęziach — natywna przekazuje pełną ścieżkę w `dir` `getSaveFileName`, fallback woła `selectFile`. `initial_name=None` → zachowanie jak dotąd.

## [0.3.3]
### Fixed
- **Repaint ramki DWM** (`winutil/dwm.py`): po zmianie koloru paska dokładamy synchroniczne `RedrawWindow(RDW_FRAME | RDW_INVALIDATE | RDW_UPDATENOW | RDW_NOCHILDREN)` (z `argtypes`, uchwyt pointer-sized). Niweluje artefakt **Windows 10** — jasne tło pod tekstem tytułu po włączeniu `DWMWA_USE_IMMERSIVE_DARK_MODE`. Domyka parzystość z GUI_STANDARD §4 (który już przewidywał `WM_NCACTIVATE` + `RedrawWindow(RDW_FRAME)`).

## [0.3.2]
### Fixed
- **DWM HWND marshaling** (`winutil/dwm.py`): wywołania `DwmSetWindowAttribute`/`SetWindowPos`/`SendMessageW` dostały jawne `argtypes` z uchwytem jako `wintypes.HWND` (pointer-sized) + `restype`. Naprawia **truncację 64-bit HWND na Win64** — bez `argtypes` ctypes marshalował goły Python int jako 32-bit `c_int`, przez co DWM/pasek tytułu działał na części okien, na innych nie. Dotyczy wszystkich konsumentów (Qt i tk). GUI_STANDARD §4 v2.9.

## [0.3.1]
### Added
- **`qt.theme.set_current_palette(palette)`** — publiczne ustawianie palety odczytywanej przez `IconProvider`, dla konsumentów z WŁASNYM motywem (np. qdarktheme): pozwala przebarwić ikony **bez przemalowania aplikacji** (żadnego `setPalette`/`setStyleSheet`). `apply_theme()` przechodzi teraz przez ten sam setter, więc istnieje dokładnie **jedno wejście zapisu** `_current` (brak rozjazdu koloru ikon z motywem UI). GUI_STANDARD §5 v2.8 sankcjonuje to jako wyjątek w ramach zasady „kolory tylko z palety".

## [0.3.0]
### Added
- **`qt/icons.py` — `IconProvider` (przebarwialne SVG Lucide)** — ekstrakcja z IcoForge (pierwszy komponent v0.3, GUI_STANDARD §5/§7):
  - `get_icon(name, color=None, size=20) -> QIcon`: podmiana `currentColor` na kolor z palety, render z obsługą HiDPI (`devicePixelRatio`), cache `(name, hex, size)`, `clear_cache()` do wołania na zmianę motywu.
  - kolory WYŁĄCZNIE z `chodzkos_gui_kit.palette` (token → pole bieżącej palety przez `current_palette()`); domyślnie `fg`, semantyczne `red`/`amber`/`accent`, token `accent_text` (dark→accent, light→accent2) dla ikon w roli tekstu (reguła kontrastu §5). Zero hexów poza `palette.py`.
  - `ICON_MAP` (akcja → plik SVG) jako jedyne miejsce zmiany zestawu; `assets/icons/` (21 ikon Lucide) + `LICENSE-icons` (ISC) pakowane do wheela.
  - bez zależności cyklicznej: `icons` zna paletę, nie `ThemeManager` (`theme` nie importuje `icons`). Integracja po stronie aplikacji: `theme_changed.connect(clear_cache)` + ponowny `setIcon`.

## [0.2.0]
### Added
- **Tor tkinter** (`tk/`, extra `[tk]`) — ekstrakcja kodu tkinter EpubForge sprzed migracji na Qt (commit `f62266b^`):
  - `tk/theme.py` — `apply_theme(root, palette)`: `ttk.Style` (clam) + rekurencyjne kolorowanie klasycznych widgetów (Listbox/Text/Canvas…); `ThemeManager.apply("auto"|"light"|"dark")` równoległy do toru Qt; auto przez `darkdetect` (None/nieznane → dark); opcjonalny `darkdetect.listener` jako wątek daemon z marshalingiem na główny wątek Tk (`root.after`); persist trybu przez wstrzyknięty `Config`. Czyste, testowalne bez wyświetlacza funkcje `palette_colors`/`widget_options` (mapowanie roli → pole `Palette`).
  - `tk/titlebar.py` — `set_titlebar_dark`/`sync_titlebar`: HWND z `GetParent(winfo_id())`, dalej WYŁĄCZNIE wspólny `winutil.dwm.set_titlebar` (ten sam DWM co tor Qt; zero duplikacji ctypes DWM); ustawiany bezwarunkowo wg motywu app (v2.5).
  - kolory wyłącznie z `palette.py` (zero hexów w `tk/*`); `tk` nie importuje PySide6.
  - testy: mapowanie palety/`widget_options`, `system_scheme` (mock `darkdetect`), titlebar; testy żywego roota Tk pod markerem `tk`, DWM pod `windows`. CI instaluje `--extra tk`.

### Changed
- spójność palety: dawne tkinterowe `LIGHT.bg2 = #f5f5f5` zastąpione wartością z `palette.py` (`#f5f5f7`, §5) — bez przenoszenia starych hexów.

## [0.1.1]
### Fixed
- dołączono marker `py.typed` (PEP 561) — konsumenci (np. EpubForge) dostają typy kitu w `mypy --strict` bez `ignore_missing_imports`

## [0.1.0]
### Added
- szkielet repo: palette.py (paleta + stany z GUI_STANDARD §5), pyproject z extras, CI, dokumentacja (README, ROADMAP, PROMPTS, CLAUDE.md), GUI_STANDARD.md v2.7
- ekstrakcja rdzenia Qt z EpubForge (PROMPTS P1):
  - `winutil/dwm.py` — `set_titlebar(hwnd, dark)`: czysty ctypes (DwmSetWindowAttribute 20/19, WM_NCACTIVATE 0→1, SetWindowPos FRAMECHANGED), zero Qt/tk, no-op poza Windows
  - `config.py` — generyczny `Config(app_name)` (platformdirs, zapis atomowy tmp+replace, `get`/`set`/`mark_dirty`/`flush`, hak `on_dirty` pod debounce, wariant portable)
  - `qt/theme.py` — `ThemeManager`: Fusion przed setPalette, paleta i `build_qss` z `palette.py` (zero lokalnych hexów), kanoniczna sekwencja `apply()` (v2.3), auto przez `colorScheme()` (Unknown→dark), `attach_titlebar`
  - `qt/titlebar.py` — `sync_titlebar`/`TitlebarSync`: DWM = motyw app BEZWARUNKOWO (v2.5), re-aplikacja przy Show/ActivationChange
  - `qt/dialogs.py` — natywny ⇔ zgodność motywów (symetrycznie, v2.2); fallback QFileDialog (sidebar, Detail, rozmiar z config, fix przycisków toolbara v2.6)
  - testy `pytest-qt` (offscreen) dla theme/titlebar/dialogs + testy `config` bez PySide6; testy DWM przygotowane pod marker `windows`
