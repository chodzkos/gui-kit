# PROMPTS — gotowe prompty Claude Code

Konwencja: jeden prompt = jedna gałąź = jeden PR. Żadnego auto-pusha.

---

## P1 — ekstrakcja rdzenia Qt z EpubForge → gui-kit (v0.1.0)

```
Pracujesz w DWÓCH repozytoriach: EpubForge (źródło) i gui-kit (cel, świeży klon
github.com/chodzkos/gui-kit). Przeczytaj w gui-kit: README.md, ROADMAP.md,
GUI_STANDARD.md §4-§5 oraz src/chodzkos_gui_kit/palette.py (już istnieje — to
jedyne źródło hexów). Przeczytaj w EpubForge: gui/theme.py, gui/titlebar*.py
(lub odpowiednik), gui/file_dialogs.py, moduł configu, testy GUI.

GAŁĄŹ (gui-kit): feat/extract-qt-core

1. winutil/dwm.py: wytnij z EpubForge czysty kod ctypes
   (DwmSetWindowAttribute(20), WM_NCACTIVATE 0→1, SetWindowPos/RedrawWindow
   RDW_FRAME) jako funkcję set_titlebar(hwnd: int, dark: bool) -> None.
   ZERO importów Qt/tk w tym module. Na nie-Windows: no-op z debug-logiem.

2. qt/theme.py: przenieś ThemeManager. WYMAGANIA (standard v2.3):
   - Fusion PRZED setPalette
   - paleta budowana z chodzkos_gui_kit.palette (usuń wszystkie lokalne hexy!)
   - QSS generowany funkcją build_qss(palette) przy KAŻDYM apply(), bez cache
   - kanoniczna sekwencja: setPalette → setStyleSheet → QToolTip.setPalette
     (ToolTipBase=bg2, ToolTipText=fg) → unpolish/polish + update() po allWidgets()
   - tryb auto: styleHints().colorScheme(), Unknown → dark; colorSchemeChanged
     podłączony tylko w auto

3. qt/titlebar.py (standard v2.5 — BEZWARUNKOWO):
   - winutil.dwm.set_titlebar(winId, app_is_dark) przy KAŻDYM apply(), na
     KAŻDYM oknie top-level; NIE pomijaj przy zgodności (atrybut DWM jest
     stanowy — pominięcie zostawia starą wartość → belka zamrożona)
   - winId w showEvent; re-aplikacja w changeEvent/ActivationChange (też bezwarunkowo)

4. qt/dialogs.py: przenieś helper (standard v2.2):
   - natywny ⇔ efektywny motyw app == motyw systemu (odczyt PRZY otwarciu)
   - fallback: instancja QFileDialog + sidebarUrls (QStandardPaths: Desktop/
     Documents/Downloads + QDir.drives + ostatni katalog z configu),
     ViewMode.Detail, ~900x550 z persist w config
   - przyciski toolbara (back/forward/toParent/newFolder + listMode/detailMode):
     PRZYCZYNA pustych = app-QSS QToolButton{padding/border} przycina przypięty
     ~22px przycisk. Fix (v2.6): per-widget QSS na QToolButton dialogu zdejmujący
     padding/border (wyższa specyficzność) + setIcon(standardIcon) gdy icon().isNull().
     NIE wymuszaj tekstu (nie mieści się w 22px). Log DEBUG objectName zostaje.
     TIMING: po setOption(DontUseNativeDialog), przed exec(). Test geometryczny
     (size vs sizeHint), nie pikselowy — działa offscreen.

5. config.py: przenieś moduł configu (platformdirs.user_config_dir, zapis
   atomowy tmp+replace, debounce). Usuń elementy specyficzne dla EpubForge —
   API generyczne: Config(app_name), get/set/mark_dirty.

6. Testy: przenieś i dostosuj testy theme/dialogs (pytest-qt, fixture qapp,
   QT_QPA_PLATFORM=offscreen). Testy wymagające realnego DWM oznacz
   @pytest.mark.windows. Testy reguły rozjazdu: mock styleHints().colorScheme().
   Test regresji tooltipów: apply(dark)→apply(light) → ToolTipBase == bg2 light
   ORAZ styleSheet bez hexów dark.

7. pytest, ruff --fix, mypy (strict). NIE modyfikuj EpubForge w tym promptcie.
8. Commit: "feat: extract qt core (theme, titlebar, dialogs, config, dwm) from EpubForge"
9. Zaproponuj push i PR. NIE pushuj automatycznie. Po merge zaproponuj tag v0.1.0.
```

---

## P2 — EpubForge przechodzi na zależność gui-kit

```
EpubForge. Warunek wstępny: gui-kit v0.1.0 jest staggowany na GitHubie.
Przeczytaj pyproject.toml, gui/theme.py, gui/titlebar*.py, gui/file_dialogs.py,
moduł configu i ich testy.

GAŁĄŹ: refactor/use-gui-kit

1. pyproject: dodaj zależność
   "chodzkos-gui-kit[qt] @ git+https://github.com/chodzkos/gui-kit@v0.1.0"
2. Podmień importy na chodzkos_gui_kit.{qt.theme, qt.titlebar, qt.dialogs,
   config, palette}. USUŃ lokalne kopie modułów i ich testy (testy logiki
   przeniesione do kitu w P1; w EpubForge zostają tylko testy integracyjne
   "aplikacja używa kitu poprawnie" — max 2-3 smoke testy).
3. Sprawdź, że w repo nie zostały ŻADNE hexy palety poza ewentualnymi assets
   (grep po #1e2028, #5DCAA5 itd.) — jeśli są, podmień na palette z kitu.
4. CHANGELOG (Changed: motyw/dialogi/titlebar/config z chodzkos-gui-kit v0.1.0).
5. pytest, ruff --fix, mypy. Uruchom aplikację (smoke: zmiana motywu w locie,
   otwarcie dialogu w auto i przy wymuszonym rozjeździe).
6. Commit: "refactor(gui): replace local theme/dialog/titlebar/config with chodzkos-gui-kit v0.1.0"
7. Zaproponuj push i PR. NIE pushuj automatycznie.
```

---

## P2b — hotfix: marker py.typed (gui-kit v0.1.1) + przywrócenie typowania w EpubForge

Powód: kit jest w pełni otypowany i przechodzi `mypy --strict`, ale v0.1.0 NIE
dołącza markera `py.typed` (PEP 561). Przez to konsumenci (EpubForge) widzą kit
jako nieotypowany — w P2 trzeba było dodać override `ignore_missing_imports` dla
`chodzkos_gui_kit.*` oraz kilka `str()/Path()` na granicy. Ten prompt domyka temat:
kit wydaje v0.1.1 z markerem, EpubForge podnosi pin i zdejmuje obejścia.

Pracujesz w DWÓCH repozytoriach: gui-kit (najpierw) i EpubForge (po wydaniu tagu).

### Część A — gui-kit (v0.1.1)

```
gui-kit. GAŁĄŹ: fix/py-typed

1. Dodaj pusty plik markera src/chodzkos_gui_kit/py.typed (PEP 561 — sygnał, że
   pakiet jest otypowany).
2. Upewnij się, że marker TRAFIA do wheela: zbuduj paczkę i sprawdź jej zawartość
   (np. `python -m build` + rozpakowanie .whl albo `hatch build` + unzip -l) —
   `chodzkos_gui_kit/py.typed` MUSI być w archiwum. Jeśli hatchling go pomija,
   dodaj go jawnie (artifacts / force-include) w pyproject.
3. Podbij wersję 0.1.0 → 0.1.1 w pyproject.toml ORAZ
   src/chodzkos_gui_kit/__init__.py (__version__).
4. CHANGELOG: nowa sekcja [0.1.1] — "Fixed: dołączono marker py.typed (PEP 561),
   konsumenci dostają typy kitu w mypy --strict".
5. pytest, ruff --fix, mypy (strict) — bez zmian w API.
6. Commit: "fix: ship py.typed marker (PEP 561)".
7. Zaproponuj push i PR. NIE pushuj automatycznie. Po merge zaproponuj tag v0.1.1.
```

### Część B — EpubForge (po staggowaniu v0.1.1)

```
EpubForge. Warunek wstępny: gui-kit v0.1.1 jest staggowany na GitHubie.
GAŁĄŹ: chore/bump-gui-kit-0-1-1

1. pyproject: podnieś pin chodzkos-gui-kit v0.1.0 → v0.1.1 (OBA wiersze:
   bazowy w [dependencies] i [qt] w extra "gui").
2. Usuń z [tool.mypy] override z modułem "chodzkos_gui_kit.*"
   (ignore_missing_imports) — kit jest już otypowany.
3. Zdejmij obejścia z granicy kitu (komentarz „bez py.typed w v0.1.0 mypy widzi Any"):
   - core/config.py: `return Path(_kit_config_dir(...))` → bez owijania w Path;
   - gui/widgets/log_view.py: `_color_for` bez owijania w str(...);
   - gui/tabs/validator.py: `_severity_color` bez str(...) wokół pól palety.
   Po zmianie mypy --strict ma przejść CZYSTO (kit dostarcza typy: Palette.bg:str,
   config_dir()->Path) — jeśli gdzieś zostaje Any, dołóż precyzyjny typ zamiast cast.
4. CHANGELOG (Changed: bump chodzkos-gui-kit → v0.1.1, przywrócono typowanie kitu).
5. pytest, ruff --fix, mypy (strict). Smoke nieobowiązkowy (brak zmian zachowania).
6. Commit: "chore(deps): bump chodzkos-gui-kit to v0.1.1, drop py.typed workarounds".
7. Zaproponuj push i PR. NIE pushuj automatycznie.
```

---

## P3 — tor tkinter (v0.2.0) — szkic, doprecyzować przy podjęciu

```
gui-kit. Źródło: kod tkinter EpubForge sprzed migracji na Qt (wskaż tag/commit).
GAŁĄŹ: feat/tk-track
1. tk/theme.py: słownik kolorów budowany z palette.py + rekurencyjne apply_theme
   (Listbox/Text/Canvas też!), darkdetect.listener jako wątek daemon.
2. tk/titlebar.py: GetParent(winfo_id()) → winutil.dwm.set_titlebar (ten sam
   moduł co Qt!), aplikacja po zmapowaniu okna (after(10)).
3. Testy palety/słownika (bez wyświetlacza); testy okienkowe markowane windows.
4. Standardowy finisz: CHANGELOG, pytest, ruff, mypy, commit, PR, tag v0.2.0.
```

---

## P4 — ekstrakcja IconProvider z IcoForge → gui-kit (v0.3.0, pierwszy komponent)

```
Pracujesz w DWÓCH repo: IcoForge (źródło, gałąź z feat/icon-system) i gui-kit (cel).
Przeczytaj w gui-kit: GUI_STANDARD.md §5 (Ikonografia), §7 (IconProvider),
src/chodzkos_gui_kit/palette.py. W IcoForge: utils/icons.py, ICON_MAP, assets/icons/,
miejsce subskrypcji theme_changed.

GAŁĄŹ (gui-kit): feat/icons

1. qt/icons.py: przenieś get_icon(name, color=None) -> QIcon.
   - kolory WYŁĄCZNIE przez chodzkos_gui_kit.palette (currentColor → token;
     domyślnie fg; semantyczne red/amber/accent; rola tekstowa w light → accent_text)
   - render 16/24 px + HiDPI (devicePixelRatio), cache (name,color,size),
     clear_cache() do wołania na theme_changed
   - ścieżki przez resource helper działający w PyInstallerze
   - ICON_MAP jako stała w module (akcja → nazwa pliku SVG)
2. assets/icons/: skopiuj używane SVG Lucide + plik LICENSE-icons (ISC).
   Dodaj do pakietu (package-data w pyproject / hatch).
3. Integracja z theme.py: po apply() motywu wyemituj/obsłuż theme_changed tak,
   by konsument mógł wywołać clear_cache()+setIcon. NIE twórz zależności
   cyklicznej icons↔theme (icons zna paletę, nie ThemeManager).
4. Test (offscreen): get_icon zwraca niepuste QIcon; ta sama nazwa w dwóch
   kolorach → różne wpisy cache; clear_cache czyści.
5. CHANGELOG, pytest, ruff --fix, mypy. Commit:
   "feat(icons): add recolorable SVG IconProvider (Lucide) from IcoForge"
6. Zaproponuj push i PR. NIE pushuj automatycznie. Po merge: konsumenci
   (IcoForge, potem EpubForge toolbary) przechodzą na chodzkos_gui_kit.qt.icons.
```

## Szablon promptu na nowy widget (v0.3+)

Przed użyciem odpowiedz sobie: **czy są DWA realne konsumenty?** Jeśli nie — widget
zostaje w aplikacji.

```
gui-kit. Nowy widget qt/widgets/<Nazwa>. Źródło: <aplikacja>/<plik> (działający kod).
Konsumenci: <app1>, <app2>. GAŁĄŹ: feat/widget-<nazwa>
1. Przenieś, generalizuj API (zero zależności od logiki aplikacji),
   kolory WYŁĄCZNIE przez palette/role QPalette.
2. Test konstrukcji + kluczowych zachowań (offscreen).
3. CHANGELOG, pytest, ruff, mypy, commit "feat(widgets): add <Nazwa>", PR.
```
