#!/usr/bin/env python3
"""Compare the Planalto index (RAW/index.json) with the Senado Federal open-data norm lists
(https://legis.senado.leg.br/dadosabertos/legislacao/lista?tipo=...&ano=...).

Writes RAW/crosscheck.json (norms known to the Senado but absent from Planalto's tables, per
type) and scripts/gaps.md (a short summary included in the README).
"""
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import net  # noqa: E402

API = "https://legis.senado.leg.br/dadosabertos/legislacao/lista?tipo={t}&ano={y}"
TYPES = {  # senado type -> (our kind, years)
    "LEI": ("lei", range(1946, 2027)),
    "LCP": ("lcp", range(1967, 2027)),
    "DEL": ("del", list(range(1937, 1947)) + list(range(1965, 1989))),
    "EMC": ("emc", range(1992, 2027)),
}
LABEL = {"lei": "Leis ordinárias", "lcp": "Leis complementares", "del": "Decretos-Lei", "emc": "Emendas Constitucionais"}


def senado(t, y):
    try:
        d = json.loads(net.get(API.format(t=t, y=y), accept="application/json"))
    except net.NotFound:
        return []
    docs = (d.get("ListaDocumento", {}).get("documentos") or {})
    docs = docs.get("documento", []) if docs else []
    return docs if isinstance(docs, list) else [docs]


def main():
    idx = json.load(open(os.path.join(net.RAW, "index.json")))
    ours = defaultdict(set)
    for e in idx:
        k = "lei" if e["kind"] == "codigo" and e.get("act_kind") == "lei" else (
            "del" if e["kind"] == "codigo" and e.get("act_kind") == "del" else e["kind"])
        num = re.sub(r"\D.*$", "", e.get("number") or "")
        if num:
            ours[(k, (e.get("date") or "")[:4])].add(num)
            ours[(k, "*")].add(num)
    missing, totals = {}, {}
    for t, (kind, years) in TYPES.items():
        miss, n = [], 0
        for y in years:
            for doc in senado(t, y):
                num = re.sub(r"\D", "", doc.get("numero") or "")
                if not num:
                    continue
                n += 1
                if num not in ours[(kind, str(y))] and num not in ours[(kind, "*")]:
                    miss.append({"norma": doc.get("normaNome"), "ementa": doc.get("ementa"), "senado_id": doc.get("id")})
        missing[kind] = miss
        totals[kind] = n
        print(f"{t}: senado {n}, missing from Planalto tables {len(miss)}")
    with open(os.path.join(net.RAW, "crosscheck.json"), "w") as f:
        json.dump({"totals": totals, "missing": missing}, f, ensure_ascii=False, indent=1)
    lines = ["- Cross-check against the Senado Federal open-data norm lists "
             "(<https://legis.senado.leg.br/dadosabertos/>), by number and year:"]
    for kind, miss in missing.items():
        ex = "; ".join(m["norma"] for m in miss[:8] if m.get("norma"))
        lines.append(f"  - {LABEL[kind]}: Senado lists {totals[kind]:,}; {len(miss):,} are absent from "
                     f"Planalto's index tables and therefore not included" + (f" (e.g. {ex})" if ex else "") + ".")
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "gaps.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
