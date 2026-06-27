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
"""

from __future__ import annotations

from collections.abc import Iterable

# Wspólny styl powierzchni (kod/blok/nagłówek tabeli): tło + tekst z palety.
_SURFACE = "background:palette(alternate-base);color:palette(text)"


def section(title: str, body: str) -> str:
    """Sekcja z nagłówkiem ``<h3>`` i dowolnym ciałem HTML."""
    return f"<h3>{title}</h3>{body}"


def paragraph(text: str) -> str:
    """Akapit ``<p>``."""
    return f"<p>{text}</p>"


def unordered_list(*items: str) -> str:
    """Lista wypunktowana ``<ul>`` z podanych elementów."""
    rows = "".join(f"<li>{item}</li>" for item in items)
    return f"<ul>{rows}</ul>"


def table(headers: Iterable[str], rows: Iterable[Iterable[str]]) -> str:
    """Tabela z nagłówkiem na ``palette(alternate-base)`` i wierszami danych."""
    th = "".join(f"<th style='padding:4px 8px;text-align:left'>{h}</th>" for h in headers)
    trs = ""
    for row in rows:
        tds = "".join(f"<td style='padding:4px 8px'>{cell}</td>" for cell in row)
        trs += f"<tr>{tds}</tr>"
    return (
        "<table border='1' cellspacing='0' cellpadding='0' "
        "style='border-collapse:collapse;margin:4px 0'>"
        f"<tr style='{_SURFACE}'>{th}</tr>{trs}</table>"
    )


def code(text: str) -> str:
    """Inline ``<code>`` na powierzchni motywu (do nazw komend/plików w zdaniu)."""
    return f"<code style='{_SURFACE};padding:1px 4px;border-radius:2px'>{text}</code>"


def preformatted(text: str) -> str:
    """Blok ``<pre>`` na powierzchni motywu (komendy wieloliniowe, listingi)."""
    style = f"{_SURFACE};padding:8px;border-radius:4px;white-space:pre-wrap"
    return f"<pre style='{style}'>{text}</pre>"
