"""Check document structure, references, fonts and page bounds after rendering."""

import json
import re
from pathlib import Path

import pymupdf

HERE = Path(__file__).resolve().parent


def main():
    data = json.loads((HERE / "content.json").read_text(encoding="utf-8"))
    decisions = {item["id"] for item in data["decisions"]}
    assert len(decisions) == len(data["decisions"]) == 60
    shown = [key for page in data["pages"] for key in page.get("decisions", [])]
    assert set(shown) == decisions and len(shown) == len(decisions)
    for item in data["decisions"]:
        for field in ("yes", "no", "why", "example", "condition", "source", "proof"):
            assert item[field], (item["id"], field)
        for target in re.findall(r"\bD\d{2}\b", item["yes"] + item["no"]):
            assert target in decisions, (item["id"], target)

    document = pymupdf.open(HERE.parent / "krpsim_verif_arbre_de_decision_eli5.pdf")
    assert len(document) == len(data["pages"])
    destinations = document.resolve_names()
    assert decisions <= destinations.keys()
    links = 0
    for index, page in enumerate(document, 1):
        text = page.get_text()
        assert f"{index} / {len(document)}" in text, index
        assert "Guide ELI5" in text, index
        assert "\ufffd" not in text, index
        for x0, y0, x1, y1, word, *_ in page.get_text("words"):
            assert 18 <= x0 <= x1 <= 824, (index, word, x0, x1)
            assert 10 <= y0 <= y1 <= 585, (index, word, y0, y1)
        for link in page.get_links():
            if link["kind"] in (pymupdf.LINK_GOTO, pymupdf.LINK_NAMED):
                assert 0 <= link["page"] < len(document), (index, link)
                if "nameddest" in link:
                    assert link["nameddest"] in destinations, (index, link)
                links += 1
        for font in page.get_fonts():
            assert any(name in font[3] for name in ("Inter", "Noto")), (index, font)
            assert document.extract_font(font[0])[3], (index, font)
        assert any("Inter" in font[3] for font in page.get_fonts()), index
    assert links >= 100, links
    result = dict(
        pages=len(document),
        decisions=len(decisions),
        internal_links=links,
        fonts="Inter regular and bold; embedded Noto fallback for Arabic digit",
        bounds="All extracted words inside page bounds",
        visual_review="See validation.md for the separate visual inspection",
    )
    (HERE / "pdf_audit.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
