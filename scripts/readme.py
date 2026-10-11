#!/usr/bin/env python3
"""Regenerate README.md from README.template.md and the files present in the repository."""
import datetime
import os
import re
from collections import Counter

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

DIRS = [
    ("constituicao", "Constituição Federal de 1988 (texto compilado, all amendments applied)"),
    ("emendas-constitucionais", "Emendas Constitucionais (EC) and Emendas Constitucionais de Revisão (ECR)"),
    ("codigos", "Codes listed in Planalto's *Códigos* table (Civil, Penal, CPC, CPP, CLT, CTN, CDC, ...)"),
    ("leis-complementares", "Leis Complementares, by year"),
    ("leis", "Leis ordinárias, by year"),
    ("leis-delegadas", "Leis Delegadas"),
    ("decretos-lei", "Decretos-Lei (1937–1946 and 1965–1988), by year"),
    ("medidas-provisorias", "Medidas Provisórias still pending / in force"),
    ("leis-imperio", "Leis do Império (1808–1889) published by Planalto, by year"),
]


def count(d):
    files = []
    for root, _, fs in os.walk(os.path.join(REPO, d)):
        files += [os.path.join(root, f) for f in fs if f.endswith(".md")]
    st = Counter()
    comp = 0
    for f in files:
        with open(f, encoding="utf-8") as fh:
            head = fh.read(3000)
        m = re.search(r"^status: (\w+)", head, re.M)
        st[m.group(1) if m else "unknown"] += 1
        if "text_version: compiled" in head:
            comp += 1
    return len(files), st, comp


def main():
    rows, total, tot_st, tot_comp = [], 0, Counter(), 0
    for d, desc in DIRS:
        if not os.path.isdir(os.path.join(REPO, d)):
            continue
        n, st, comp = count(d)
        total += n
        tot_st.update(st)
        tot_comp += comp
        rows.append(f"| `{d}/` | {desc} | {n:,} | {st.get('in_force', 0):,} | {st.get('repealed', 0):,} | {comp:,} |")
    table = "\n".join(["| Directory | Content | Files | `in_force` | `repealed` | from *texto compilado* |",
                       "|---|---|---:|---:|---:|---:|"] + rows +
                      [f"| **Total** | | **{total:,}** | **{tot_st.get('in_force', 0):,}** | **{tot_st.get('repealed', 0):,}** | **{tot_comp:,}** |"])
    tpl = open(os.path.join(REPO, "scripts", "README.template.md"), encoding="utf-8").read()
    gp = os.path.join(REPO, "scripts", "gaps.md")
    gaps = open(gp, encoding="utf-8").read().rstrip() if os.path.exists(gp) else ""
    out = tpl.replace("{{GAPS}}", gaps).replace("{{TABLE}}", table).replace("{{TOTAL}}", f"{total:,}").replace(
        "{{DATE}}", datetime.date.today().isoformat())
    with open(os.path.join(REPO, "README.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(out)
    print(table)


if __name__ == "__main__":
    main()
