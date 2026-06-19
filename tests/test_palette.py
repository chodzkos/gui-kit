"""Testy warstwy 0 — muszą przechodzić bez PySide6/tk."""
import re

from chodzkos_gui_kit import palette

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def test_palettes_complete_and_valid() -> None:
    for pal in (palette.DARK, palette.LIGHT):
        for field, value in vars(pal).items():
            if field == "name":
                continue
            assert HEX.match(value), f"{pal.name}.{field} = {value!r}"


def test_unknown_falls_back_to_dark() -> None:
    assert palette.get("unknown") is palette.DARK


def test_light_accent_text_uses_accent2() -> None:
    # reguła kontrastu GUI_STANDARD §5
    assert palette.LIGHT.accent_text == palette.LIGHT.accent2
    assert palette.DARK.accent_text == palette.DARK.accent


def test_brand_accent_is_marketing_green() -> None:
    # znak rozpoznawczy marki (GUI_STANDARD §5) — niezmiennik, pinujemy hex
    assert palette.DARK.accent == "#5DCAA5"
