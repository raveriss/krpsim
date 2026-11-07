"""Validate connected nodes, visible arrows, cross-page references and PDF bounds."""

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pymupdf
from build_connected import check_graph

HERE = Path(__file__).resolve().parent


def main():
    graphs = json.loads((HERE / "graphs.json").read_text(encoding="utf-8"))
    registry = {graph["id"]: graph for graph in graphs}
    reached = {"G01"}
    for _ in graphs:
        reached |= {ref for key in list(reached) for ref in registry[key]["calls"]}
    assert reached == registry.keys()
    decisions = set()
    arrow_count = 0
    node_count = 0
    ns = {"s": "http://www.w3.org/2000/svg"}
    for graph in graphs:
        check_graph(graph)
        tree = ET.parse(HERE / f'{graph["id"]}.svg')
        nodes = tree.findall('.//s:g[@class="node"]', ns)
        edges = tree.findall('.//s:g[@class="edge"]', ns)
        assert len(nodes) == len(graph["nodes"])
        assert len(edges) == len(graph["edges"])
        for edge in edges:
            assert edge.find("s:path", ns) is not None
            assert edge.find("s:polygon", ns) is not None
        arrow_count += len(edges)
        node_count += len(nodes)
        decisions |= {
            node["id"] for node in graph["nodes"] if node["id"].startswith("D")
        }
    assert decisions == {f"D{i:02}" for i in range(1, 61)}
    metrics = json.loads((HERE / "graph_audit.json").read_text(encoding="utf-8"))
    assert min(metric["question_pt"] for metric in metrics) >= 11
    pdf = pymupdf.open(HERE.parent.parent / "krpsim_verif_arbre_de_decision_relie.pdf")
    assert len(pdf) == len(graphs) + 2
    destinations = pdf.resolve_names()
    assert registry.keys() <= destinations.keys()
    for number, page in enumerate(pdf, 1):
        assert f"{number} / {len(pdf)}" in page.get_text()
        for x0, y0, x1, y1, text, *_ in page.get_text("words"):
            assert 18 <= x0 < x1 <= page.rect.width - 18, (number, text)
            assert 10 <= y0 < y1 <= page.rect.height - 10, (number, text)
        for font in page.get_fonts():
            assert "Inter" in font[3]
            assert pdf.extract_font(font[0])[3]
        for link in page.get_links():
            assert 0 <= link["page"] < len(pdf), (number, link)
    result = dict(
        pages=len(pdf),
        connected_graphs=len(graphs),
        nodes=node_count,
        drawn_arrows=arrow_count,
        referenced_decisions=len(decisions),
        minimum_question_size_pt=min(metric["question_pt"] for metric in metrics),
        graph_connectivity="Every node reachable from its graph entry",
        global_navigation="Every graph reachable from G01 through named references",
        visual_review="See README.md for the separate visual inspection",
    )
    (HERE / "validation.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
