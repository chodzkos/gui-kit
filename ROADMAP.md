# ROADMAP — chodzkos-gui-kit

Zasada nadrzędna: **reguła trzech / ekstrakcja zamiast pisania na zapas.**
Do kitu wchodzi wyłącznie kod sprawdzony w działającej aplikacji; widget bez
dwóch realnych konsumentów nie wchodzi wcale.

## v0.1.0 — ekstrakcja rdzenia Qt (z EpubForge)

- [x] szkielet repo, pyproject (extras qt/tk/dev), CI
- [x] `palette.py` — paleta + stany pochodne z GUI_STANDARD §5 (czyste dane)
- [x] `config.py` — ekstrakcja z EpubForge (platformdirs, zapis atomowy, debounce)
- [x] `winutil/dwm.py` — ekstrakcja ctypes DWM (WM_NCACTIVATE, RDW_FRAME) jako kod bez Qt/tk
- [x] `qt/theme.py` — kanoniczna sekwencja apply() (standard v2.3), generator QSS z palette
- [x] `qt/titlebar.py` — DWM = motyw app bezwarunkowo (standard v2.5)
- [x] `qt/dialogs.py` — natywny⇔zgodność + skonfigurowany fallback (standard v2.2)
- [x] migracja testów z EpubForge (pytest-qt, offscreen; testy DWM markowane `windows`)
- [ ] tag `v0.1.0` → EpubForge przechodzi na zależność (PROMPTS P2)

## v0.2.0 — tor tkinter

- [x] `tk/theme.py` — palette_colors/widget_options z palette.py + rekurencyjne apply_theme + darkdetect
- [x] `tk/titlebar.py` — GetParent(winfo_id) → winutil.dwm
- [x] źródło ekstrakcji: kod tkinter EpubForge sprzed migracji (commit `f62266b^`, przed PR #22)
- [ ] pierwsza konsumpcja: najbliższe małe narzędzie wg tabeli decyzyjnej §2

## v0.3.0 — widgety wspólne (TYLKO na żądanie drugiej aplikacji)

Kandydaci (z GUI_STANDARD §7), każdy wchodzi dopiero gdy ma 2 konsumentów:
- [ ] `qt/icons.py` (`IconProvider` / `get_icon`) — PIERWSZY w kolejce: zależy
      od tej samej palety i sygnału `theme_changed` co `theme.py`, więc
      naturalnie domyka tor motywu. Źródło: IcoForge `feat/icon-system`
      (kroki 4.1–4.6). Wnosi też `assets/icons/` (Lucide ISC) + LICENSE-icons.
      Konsumenci: IcoForge + EpubForge/pdf2md (toolbary).
- [ ] `qt/widgets/PathEntry` (pole + „…")
- [ ] `qt/widgets/FileList` (toolbar + licznik + D&D)
- [ ] `qt/widgets/Section`, `AboutPanel`, `LogStreamer`
- [ ] prawdopodobni konsumenci: EpubForge + IcoForge (lifting) lub pdf2md (etap G1)

## v0.4.0 — most do mobile (opcjonalnie)

- [ ] eksport tokenów palety do JSON (`palette export`)
- [ ] generator `theme.dart` dla Fluttera (mapowanie na role Material 3 wg MOBILE_STANDARD §4)
- [ ] cel: jeden commit zmiany koloru marki propaguje się na desktop + mobile

## v1.0.0 — stabilizacja API

- [ ] zamrożenie publicznych sygnatur (apply, attach_titlebar, dialogs)
- [ ] od v1.0: zmiana sygnatury lub reguły (rozjazd, sekwencja apply) = MAJOR

## Poza zakresem (świadomie)

- publikacja na PyPI — dopóki jedynym konsumentem są własne aplikacje, git+tag wystarcza
- wsparcie PyQt5/6 — tylko PySide6 (licencja + jeden tor utrzymania)
- motywy inne niż dark/light marki — kit implementuje standard, nie jest biblioteką ogólną
