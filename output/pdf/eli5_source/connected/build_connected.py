"""Render connected flowcharts, with actual edges, from the editable graph data."""

import html
import json
import re
import subprocess
import textwrap
from pathlib import Path

from weasyprint import HTML

HERE = Path(__file__).resolve().parent


def label(text, width, size):
    lines = []
    for paragraph in text.split("\n"):
        lines.extend(textwrap.wrap(paragraph, width, break_long_words=False) or [""])
    return (
        f'<FONT POINT-SIZE="{size}">'
        + "<BR/>".join(html.escape(line) for line in lines)
        + "</FONT>"
    )


def node_dot(node):
    kind = node.get("kind", "action")
    shape, color = {
        "action": ("box", "#edf4fa"),
        "call": ("box", "#e3f1f3"),
        "decision": ("diamond", "#fff3cd"),
        "end": ("ellipse", "#e2f2e7"),
        "error": ("ellipse", "#fbe7e2"),
        "connector": ("ellipse", "#e3f1f3"),
    }[kind]
    code = node.get("code", "")
    body = label(node["text"], 36 if kind == "decision" else 42, 13)
    if code:
        body += "<BR/>" + label(code, 46, 10.5)
    peripheries = 2 if kind == "call" else 1
    style = "filled,rounded" if shape == "box" else "filled"
    return (
        f'{node["id"]} [shape={shape}, style="{style}", '
        f'fillcolor="{color}", peripheries={peripheries}, label=<{body}>];'
    )


def graph_dot(graph):
    lines = [
        "digraph flow {",
        "graph [rankdir=TB, ranksep=0.28, nodesep=0.25, "
        'pad=0.12, splines=polyline, bgcolor="transparent", ordering=out];',
        'node [fontname="Inter", fontsize=13, color="#66869b", '
        'fontcolor="#172e43", penwidth=1.1, margin="0.13,0.09"];',
        'edge [fontname="Inter", fontsize=11, color="#486d84", '
        'fontcolor="#235d6d", penwidth=1.15, arrowsize=0.7];',
    ]
    lines.extend(node_dot(node) for node in graph["nodes"])
    for edge in graph["edges"]:
        label_key = "xlabel" if edge.get("loop") else "label"
        options = [
            f'{label_key}={json.dumps(edge.get("label", ""), ensure_ascii=False)}'
        ]
        if edge.get("loop"):
            options.append("constraint=false")
            if any(
                other["from"] == edge["to"] and other["to"] == edge["from"]
                for other in graph["edges"]
            ):
                options.extend(["tailport=w", "headport=w"])
        if edge.get("port"):
            options.append(f'tailport={edge["port"]}')
        lines.append(f'{edge["from"]} -> {edge["to"]} [{", ".join(options)}];')
    for group in graph.get("same_rank", []):
        lines.append("{rank=same; " + "; ".join(group) + ";}")
    return "\n".join(lines + ["}"])


def check_graph(graph):
    ids = {n["id"] for n in graph["nodes"]}
    assert len(ids) == len(graph["nodes"]), graph["id"]
    reached = {graph["nodes"][0]["id"]}
    for edge in graph["edges"]:
        assert edge["from"] in ids and edge["to"] in ids
    while True:
        added = {e["to"] for e in graph["edges"] if e["from"] in reached}
        if added <= reached:
            break
        reached |= added
    assert reached == ids, (graph["id"], ids - reached)
    for node in graph["nodes"]:
        outgoing = [e for e in graph["edges"] if e["from"] == node["id"]]
        if node["kind"] == "decision":
            assert {e["label"] for e in outgoing} == {"Oui", "Non"}, node
        if not outgoing:
            assert node["kind"] in ("end", "error", "connector"), node


def main():
    graphs = json.loads((HERE / "graphs.json").read_text(encoding="utf-8"))
    css = (HERE / "style.css").read_text(encoding="utf-8")
    pages = []
    metrics = []
    count = len(graphs) + 2
    index_rows = []
    for position, graph in enumerate(graphs, 3):
        check_graph(graph)
        dot_path = HERE / f'{graph["id"]}.dot'
        svg_path = dot_path.with_suffix(".svg")
        dot_path.write_text(graph_dot(graph), encoding="utf-8")
        subprocess.run(["dot", "-Tsvg", str(dot_path), "-o", str(svg_path)], check=True)
        svg = svg_path.read_text(encoding="utf-8")
        width, height = map(
            float, re.search(r'width="([\d.]+)pt" height="([\d.]+)pt"', svg).groups()
        )
        landscape_scale = min(1100 / width, 620 / height, 1)
        portrait_scale = min(760 / width, 970 / height, 1)
        orientation = "landscape" if landscape_scale >= portrait_scale else "portrait"
        scale = max(landscape_scale, portrait_scale)
        metrics.append(
            dict(
                id=graph["id"],
                width=width,
                height=height,
                scale=scale,
                question_pt=13 * scale,
                nodes=len(graph["nodes"]),
                edges=len(graph["edges"]),
            )
        )
        assert 13 * scale >= 11, (graph["id"], width, height, scale)
        index_rows.append(
            f'<a href="#{graph["id"]}"><b>{graph["id"]}</b> '
            f'{html.escape(graph["title"])}<span>{position}</span></a>'
        )
        refs = " · ".join(
            f'<a href="#{ref}">{ref}</a>' for ref in graph.get("calls", [])
        )
        pages.append(
            f'<section id="{graph["id"]}" class="page {orientation}">'
            '<div class="eyebrow">KRPSIM_VERIF / ARBRE DE DÉCISION RELIÉ</div>'
            f'<h1>{graph["id"]} · {html.escape(graph["title"])}</h1>'
            f'<p class="subtitle">{html.escape(graph["function"])}</p>'
            f'<div class="drawing"><img src="{svg_path.name}" '
            f'style="width:{width * scale}pt;height:{height * scale}pt"></div>'
            f'<p class="note">{html.escape(graph["note"])}</p>'
            f'<p class="source">Sources : {html.escape(graph["source"])}'
            f'<br>Schémas liés : {refs or "retour au schéma appelant"}</p>'
            f"<footer><span>Code 268075e · ELI5 + identifiants Python</span>"
            f"<span>{position} / {count}</span></footer></section>"
        )
    cover = f"""<section class="page landscape cover" id="cover">
      <div class="eyebrow">KRPSIM / COMPRENDRE LE CHEMIN DU PROGRAMME</div>
      <h1>krpsim_verif<br>Les décisions reliées</h1>
      <p class="lead">Des flèches pour suivre chaque chemin.<br>
      Du français simple pour comprendre chaque choix.</p>
      <div class="legend"><b>Début</b> → Action → <b>Question Oui / Non</b>
      → Action suivante → <b>Fin ou retour</b></div>
      <p>Les branches, les retours de boucle et les sorties sont dessinés.
      Les noms des fonctions et des variables restent visibles dans les nœuds.</p>
      <p>Chaque rectangle à double bord ouvre une fonction ou un sous-parcours :
      ouvrir le schéma Gxx indiqué, puis revenir suivre la flèche de retour.</p>
      <p>Les erreurs interrompent le parcours en cours et reviennent à G02,
      qui montre les messages et codes de sortie.</p>
      <p>Les questions « Reste-t-il… ? » rendent visibles les boucles du code.</p>
      <div class="panel">Commencer par <b>G01</b>, puis suivre les flèches.
      Les fiches détaillées, exemples et exercices restent disponibles dans
      le guide ELI5 livré séparément.</div>
      <p class="source">7 novembre 2026 · krpsim 0.1.1 · code local 268075e.
      La vérification rejoue les départs ; elle ne recherche pas une trace optimale.</p>
      <footer><span>Version avec logigrammes connectés</span>
      <span>1 / {count}</span></footer>
      </section>"""
    toc = (
        '<section class="page landscape" id="toc">'
        '<div class="eyebrow">NAVIGATION / SOMMAIRE CLIQUABLE</div>'
        "<h1>Suivre les appels, puis revenir</h1>"
        '<p class="subtitle">Les identifiants Dxx correspondent aux décisions '
        'du guide ELI5 et de sa matrice.</p><div class="toc">'
        + "".join(index_rows)
        + "</div><footer><span>Les nœuds d’un même schéma sont tous reliés.</span>"
        f"<span>2 / {count}</span></footer></section>"
    )
    document = (
        '<!doctype html><html lang="fr"><head><meta charset="utf-8">'
        "<title>krpsim_verif - Arbre de décision relié</title><style>"
        + css
        + "</style></head><body>"
        + cover
        + toc
        + "".join(pages)
        + "</body></html>"
    )
    (HERE / "arbre.html").write_text(document, encoding="utf-8")
    HTML(filename=str(HERE / "arbre.html")).write_pdf(
        HERE.parent.parent / "krpsim_verif_arbre_de_decision_relie.pdf"
    )
    (HERE / "graph_audit.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{count} pages, {len(graphs)} connected graphs.")


if __name__ == "__main__":
    main()
