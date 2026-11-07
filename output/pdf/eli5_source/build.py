"""Rebuild the French guide from editable JSON, HTML and embedded Inter fonts."""

import csv
import html
import json
from pathlib import Path

from weasyprint import HTML

HERE = Path(__file__).resolve().parent
DATA = json.loads((HERE / "content.json").read_text(encoding="utf-8"))


def esc(value):
    return html.escape(str(value))


def links(text):
    """Link explicit decision references without altering ordinary prose."""
    import re

    return re.sub(r"\bD\d{2}\b", lambda m: f'<a href="#{m[0]}">{m[0]}</a>', esc(text))


def decision(item):
    """A local flowchart with explicit branches and a source beside each node."""
    return f"""<article class="decision" id="{item['id']}">
      <div class="decision-top">
        <div class="question">
          <svg viewBox="0 0 400 100" preserveAspectRatio="none">
            <polygon points="200,1 399,50 200,99 1,50" fill="#fff4d4"
                     stroke="#b58b30" stroke-width="1.2"/>
          </svg>
          <div class="question-text"><b>{item['id']}</b><br>
            {esc(item['question'])}</div>
        </div>
        <div class="branches">
          <div class="branch"><span>Oui →</span><div>{links(item['yes'])}</div></div>
          <div class="branch"><span>Non →</span><div>{links(item['no'])}</div></div>
        </div>
      </div>
      <div class="source"><b>{esc(item['function'])}</b> · {esc(item['source'])}
      <br><code>{esc(item['condition'])}</code></div>
      <div class="explanation"><b>Pourquoi :</b> {esc(item['why'])}<br>
      <b>Exemple :</b> {esc(item['example'])}</div>
    </article>"""


def table(headers, rows, cls=""):
    return (
        f'<table class="{cls}"><thead><tr>'
        + "".join(f"<th>{esc(h)}</th>" for h in headers)
        + "</tr></thead><tbody>"
        + "".join(
            "<tr>" + "".join(f"<td>{links(v)}</td>" for v in row) + "</tr>"
            for row in rows
        )
        + "</tbody></table>"
    )


def main():
    pages = DATA["pages"]
    registry = {item["id"]: item for item in DATA["decisions"]}
    sections = []
    for index, page in enumerate(pages, 1):
        content = page.get("html", "")
        if "decisions" in page:
            content += "".join(decision(registry[key]) for key in page["decisions"])
        if "table" in page:
            content += table(page["table"]["headers"], page["table"]["rows"])
        if page.get("toc"):
            content += (
                '<div class="toc">'
                + "".join(
                    f'<a href="#{p["id"]}"><span>{esc(p["title"])}</span>'
                    f"<b>{i}</b></a>"
                    for i, p in enumerate(pages, 1)
                    if p.get("toc_entry")
                )
                + "</div>"
            )
        if page.get("matrix"):
            content += table(
                ["Décision", "Fonction / source", "Chemins Oui / Non", "Preuve"],
                [
                    [
                        key + " · " + registry[key]["question"],
                        registry[key]["function"] + "\n" + registry[key]["source"],
                        "Oui : "
                        + registry[key]["yes"]
                        + "\nNon : "
                        + registry[key]["no"],
                        registry[key]["proof"],
                    ]
                    for key in page["matrix"]
                ],
                "matrix",
            )
        sections.append(
            f'<section class="page {page.get("class", "")}" id="{page["id"]}">'
            f'<div class="eyebrow">KRPSIM / COMPRENDRE ET RETROUVER LE CODE</div>'
            f'<h1>{esc(page["title"])}</h1>'
            f'<p class="subtitle">{esc(page.get("subtitle", ""))}</p>'
            f"<main>{content}</main>"
            f'<footer><span>Code {DATA["revision"]} · {DATA["date"]} · '
            f"Guide ELI5</span><span>{index} / {len(pages)}</span></footer></section>"
        )
    document = (
        '<!doctype html><html lang="fr"><head><meta charset="utf-8">'
        "<title>Comprendre krpsim_verif</title><style>"
        + (HERE / "style.css").read_text(encoding="utf-8")
        + "</style></head><body>"
        + "".join(sections)
        + "</body></html>"
    )
    output = HERE / "guide.html"
    output.write_text(document, encoding="utf-8")
    HTML(filename=str(output)).write_pdf(
        HERE.parent / "krpsim_verif_arbre_de_decision_eli5.pdf"
    )
    with (HERE / "matrice_tracabilite.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=list(DATA["decisions"][0]))
        writer.writeheader()
        writer.writerows(DATA["decisions"])
    print(f"Generated {len(pages)} pages, {len(registry)} decisions.")


if __name__ == "__main__":
    main()
