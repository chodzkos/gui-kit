"""Helpery składania treści pomocy jako HTML motyw-świadomy (warstwa ``qt/widgets``).

Treść okna :class:`~chodzkos_gui_kit.qt.widgets.help_window.HelpWindow` to czysty
HTML — konsument składa go tymi funkcjami zamiast pisać znaczniki ręcznie. Kolory
powierzchni (tła kodu, tabel, bloków) idą WYŁĄCZNIE przez ``palette(...)`` Qt:
``palette(alternate-base)`` na tło i ``palette(text)`` na tekst — para trzymająca
kontrast w obu motywach. ZERO zaszytych hexów.

``QTextBrowser`` rozwiązuje ``palette(...)`` do KONKRETNYCH kolorów dopiero przy
``setHtml`` i NIE aktualizuje ich przy zmianie motywu — dlatego treść jest
re-renderowana (ten sam HTML, ``setHtml`` ponownie) na ``PaletteChange``; patrz
:meth:`HelpWindow.changeEvent`. Funkcje tutaj zwracają więc statyczny HTML z
literalnymi ``palette(...)`` — bez wiązania z konkretną paletą.

Granica zaufania (escaping)
---------------------------
Wynik trafia SUROWO do ``QTextBrowser.setHtml`` (nie ma osobnego escapowania po
drodze), więc rozdzielamy helpery na dwie grupy:

* **Helpery treści (liście)** — :func:`code`, :func:`preformatted`, oraz komórki
  i nagłówki :func:`table` — dostają TEKST, który może zawierać ``<``/``>``/``&``
  (nazwy komend, ścieżki, listingi z przekierowaniami powłoki). Escapują wejście
  przez :func:`html.escape`, więc podaje się im surowy tekst, a znaki specjalne
  renderują się dosłownie. Bezpieczne dla treści dynamicznej.
* **Helpery struktury** — :func:`section`, :func:`paragraph`, :func:`unordered_list`
  — to punkty SKŁADANIA: ich argumenty są wstawiane do HTML BEZ escapowania, więc
  MUSZĄ być zaufanym/wcześniej-zescapowanym HTML (np. wynik helperów-liści albo
  statyczny tekst autora). Tekst dynamiczny wstawiaj przez helpery-liście, a jeśli
  musi trafić wprost do tych funkcji — zescapuj go po stronie konsumenta::

    import html
    from chodzkos_gui_kit.qt.widgets import help_html

    # OK: dynamiczna nazwa komendy przez helper-liść (escapowane automatycznie)
    help_html.paragraph(f"Uruchom {help_html.code(user_cmd)} w katalogu projektu.")

    # OK: dynamiczny tekst wprost do helpera-struktury — zescapuj samodzielnie
    help_html.paragraph(html.escape(user_supplied_text))
"""

from __future__ import annotations

import html
from collections.abc import Iterable

# Wspólny styl powierzchni (kod/blok/nagłówek tabeli): tło + tekst z palety.
_SURFACE = "background:palette(alternate-base);color:palette(text)"


def section(title: str, body: str) -> str:
    """Sekcja z nagłówkiem ``<h3>`` i dowolnym ciałem HTML.

    Helper STRUKTURY: ``title`` i ``body`` wstawiane BEZ escapowania — podawaj
    zaufany/zescapowany HTML (np. wynik :func:`paragraph`/:func:`table`).
    """
    return f"<h3>{title}</h3>{body}"


def paragraph(text: str) -> str:
    """Akapit ``<p>``.

    Helper STRUKTURY: ``text`` wstawiany BEZ escapowania (pozwala zagnieżdżać
    inline HTML, np. :func:`code`). Tekst dynamiczny zescapuj po stronie
    konsumenta (``html.escape``) albo złóż go z helperów-liści.
    """
    return f"<p>{text}</p>"


def unordered_list(*items: str) -> str:
    """Lista wypunktowana ``<ul>`` z podanych elementów.

    Helper STRUKTURY: ``items`` wstawiane BEZ escapowania — podawaj zaufany
    HTML (np. ``code(...)`` w elemencie) albo tekst zescapowany po stronie
    konsumenta.
    """
    rows = "".join(f"<li>{item}</li>" for item in items)
    return f"<ul>{rows}</ul>"


def table(headers: Iterable[str], rows: Iterable[Iterable[str]]) -> str:
    """Tabela z nagłówkiem na ``palette(alternate-base)`` i wierszami danych.

    Helper TREŚCI: nagłówki i komórki to tekst danych — są escapowane
    (:func:`html.escape`), więc podawaj surowe ciągi (``<``/``&`` renderują się
    dosłownie). Tabela to dane, nie punkt zagnieżdżania HTML.
    """
    th = "".join(
        f"<th style='padding:4px 8px;text-align:left'>{html.escape(h, quote=False)}</th>"
        for h in headers
    )
    trs = ""
    for row in rows:
        tds = "".join(
            f"<td style='padding:4px 8px'>{html.escape(cell, quote=False)}</td>" for cell in row
        )
        trs += f"<tr>{tds}</tr>"
    return (
        "<table border='1' cellspacing='0' cellpadding='0' "
        "style='border-collapse:collapse;margin:4px 0'>"
        f"<tr style='{_SURFACE}'>{th}</tr>{trs}</table>"
    )


def code(text: str) -> str:
    """Inline ``<code>`` na powierzchni motywu (do nazw komend/plików w zdaniu).

    Helper TREŚCI: ``text`` jest escapowany (:func:`html.escape`) — podawaj surowy
    tekst (np. ``code("a < b")`` renderuje się dosłownie, nie jako znacznik).
    """
    inner = html.escape(text, quote=False)
    return f"<code style='{_SURFACE};padding:1px 4px;border-radius:2px'>{inner}</code>"


def preformatted(text: str) -> str:
    """Blok ``<pre>`` na powierzchni motywu (komendy wieloliniowe, listingi).

    Helper TREŚCI: ``text`` jest escapowany (:func:`html.escape`) — podawaj surowy
    listing (przekierowania powłoki ``>``/``<``, ``&`` renderują się dosłownie).
    """
    style = f"{_SURFACE};padding:8px;border-radius:4px;white-space:pre-wrap"
    return f"<pre style='{style}'>{html.escape(text, quote=False)}</pre>"
