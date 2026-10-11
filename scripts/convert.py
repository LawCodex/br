#!/usr/bin/env python3
"""Convert the cached Planalto pages (see fetch.py) to Markdown files in the repository.

Usage: python scripts/convert.py [--kinds lei,del,...] [--out DIR]
Writes RAW/convert_report.json with per-file details (status, compiled or not, struck text).
"""
import argparse
import concurrent.futures as cf
import datetime
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import net  # noqa: E402
import planalto_md as P  # noqa: E402
from select_norms import compiled_url, selected  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
TODAY = datetime.date.today().isoformat()

MONTHS = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
          "setembro", "outubro", "novembro", "dezembro"]

KIND = {
    #  kind: (type, label, urn type, directory, file prefix, by_year)
    "constituicao": ("constitution", "Constituição", "constituicao", "constituicao", "constituicao", False),
    "emc": ("constitutional_amendment", "Emenda Constitucional", "emenda.constitucional", "emendas-constitucionais", "ec", False),
    "ecr": ("constitutional_amendment", "Emenda Constitucional de Revisão", "emenda.constitucional.revisao", "emendas-constitucionais", "ecr", False),
    "codigo": ("code", None, None, "codigos", None, False),
    "lcp": ("complementary_law", "Lei Complementar", "lei.complementar", "leis-complementares", "lcp", True),
    "lei": ("act", "Lei", "lei", "leis", "lei", True),
    "ldl": ("delegated_law", "Lei Delegada", "lei.delegada", "leis-delegadas", "ldl", False),
    "del": ("decree_law", "Decreto-Lei", "decreto.lei", "decretos-lei", "del", True),
    "mpv": ("provisional_measure", "Medida Provisória", "medida.provisoria", "medidas-provisorias", "mpv", False),
    "lim": ("act", "Lei", "lei", "leis-imperio", "lim", True),
}


def slug(s, maxlen=80):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:maxlen].strip("-")


def fmt_num(n):
    """'8078' -> '8.078', '2200-2' -> '2.200-2'."""
    m = re.match(r"^(\d+)(.*)$", n or "")
    if not m:
        return n
    d = m.group(1)
    if len(d) > 3:
        d = f"{int(d):,}".replace(",", ".")
    return d + m.group(2)


def long_date(iso):
    if not iso:
        return ""
    y, m, d = iso.split("-")
    d = int(d)
    return f"{'1º' if d == 1 else d} de {MONTHS[int(m) - 1]} de {y}"


def yaml_str(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


REPEAL_START = re.compile(
    r"(^|\()\s*(revogad[oa]\s+(pel|integralmente|tacitamente|expressamente)|vig[êe]ncia\s+encerrada|"
    r"sem\s+efic[áa]cia|rejeitad[oa]|convertid[oa]\s|tornad[oa]\s+sem\s+efeito|caducou|perdeu\s+a\s+efic[áa]cia)", re.I)
REPEAL_ANY = re.compile(r"(?<!parcialmente )\brevogad[oa]\s+pel[oa]\s+(lei|lcp|lc\b|decreto|del\b|medida|mp\b|emenda|ato|resolu)", re.I)


def detect_status(notes, kind):
    """Planalto puts whole-act annotations such as 'Revogada pela Lei nº 13.105, de 2015' in the
    header of the page, between the title and the ementa (provision-level annotations are
    written next to each provision instead)."""
    for n in notes:
        m = REPEAL_START.search(n) or REPEAL_ANY.search(n)
        if m:
            return "repealed", n
    return "in_force", None


def target_path(e, code_names):
    kind = e["kind"]
    typ, label, urnt, d, prefix, by_year = KIND[kind]
    year = (e.get("date") or "0000")[:4]
    num = (e.get("number") or "").lower()
    if kind == "constituicao":
        return os.path.join(d, "constituicao-1988.md")
    if kind == "codigo":
        name = slug(e["code_name"], 60)
        ak = {"lei": "lei", "del": "del", "dec": "decreto"}[e.get("act_kind", "lei")]
        return os.path.join(d, f"{name}-{ak}-{e['number']}-{year}.md")
    if kind in ("emc", "ecr"):
        return os.path.join(d, f"{prefix}-{int(num.split('-')[0]):03d}-{year}.md")
    if kind == "lim":
        base = slug(e["url"].split("/")[-1].rsplit(".", 1)[0], 60)
        return os.path.join(d, year, f"{prefix}-{e['date'] or 'sd'}-{base}.md")
    name = f"{prefix}-{slug(num)}-{year}.md"
    if by_year:
        return os.path.join(d, year, name)
    return os.path.join(d, name)


def urn(e):
    kind = e["kind"]
    if kind == "constituicao":
        return "urn:lex:br:federal:constituicao:1988-10-05;1988"
    if kind == "codigo":
        t = {"lei": "lei", "del": "decreto.lei", "dec": "decreto"}[e.get("act_kind", "lei")]
        return f"urn:lex:br:federal:{t}:{e['date']};{e['number']}" if e.get("date") else ""
    urnt = KIND[kind][2]
    if kind == "lim":
        return f"urn:lex:br:federal:lei:{e['date']};s/n" if e.get("date") else ""
    return f"urn:lex:br:federal:{urnt}:{e['date']};{(e['number'] or '').lower()}" if e.get("date") else ""


def title_of(e, page_title):
    kind = e["kind"]
    if kind == "constituicao":
        return "Constituição da República Federativa do Brasil de 1988"
    if kind == "codigo":
        return e["code_name"]
    if kind == "lim":
        return page_title.title() if page_title else f"Lei de {long_date(e['date'])}"
    label = KIND[kind][1]
    t = f"{label} nº {fmt_num(e['number'])}"
    if e.get("date"):
        t += f", de {long_date(e['date'])}"
    return t


def convert_one(e, code_urls, out_root):
    kind = e["kind"]
    if kind in ("lei", "del") and e["url"].lower() in code_urls:
        return None  # published under codigos/
    try:
        page = net.decode(net.get(e["url"]))
    except net.NotFound:
        return {"url": e["url"], "kind": kind, "error": "404"}
    src = e["url"]
    compiled = False
    cu = compiled_url(e["url"], page)
    if cu:
        try:
            page = net.decode(net.get(cu))
            src = cu
            compiled = True
        except net.NotFound:
            pass
    parsed = P.parse(page)
    ptitle, notes, ementa, body = P.split_header(parsed["items"], e.get("ementa"))
    if kind in ("constituicao", "emc", "ecr"):
        status, why = "in_force", None
    else:
        # whole-act annotations sit in the header; when the whole text is struck through the
        # parser may not find the enacting formula, so also look at the lines before the first article
        pre = []
        for k_, t_ in body[:40]:
            if k_ == "p" and P.ART_RE.match(t_):
                break
            if k_ == "p" and len(t_) < 250 and not P.ENACT_RE.match(t_):
                pre.append(t_)
        status, why = detect_status(notes + pre[:12], kind)
    if kind == "mpv" and status == "repealed":
        # Planalto's MP table still says "Em Tramitação" but the MP page says it was revoked
        return {"url": e["url"], "kind": kind, "skipped": "mpv revoked: " + (why or "")}
    if not ementa:
        ementa = e.get("ementa") or ""
    title = title_of(e, ptitle)
    lines_body = P.to_markdown_body(body)
    if not any(l.strip() for l in lines_body):
        return {"url": e["url"], "kind": kind, "error": "empty"}

    fm = ["---", f"title: {yaml_str(title)}"]
    if kind == "codigo":
        fm.append(f"act: {yaml_str(e['code_ref'])}")
    ident = urn(e)
    if ident:
        fm.append(f"identifier: {yaml_str(ident)}")
    fm += [f"type: {KIND[kind][0]}", "jurisdiction: br", "language: pt"]
    if e.get("date"):
        fm.append(f"date: {e['date']}")
    fm.append(f"status: {status}")
    if why:
        fm.append(f"status_note: {yaml_str(why)}")
    if kind == "mpv":
        fm.append(f"situacao_planalto: {yaml_str((e.get('situacao') or '').split('Originária')[0].strip() or 'Em Tramitação')}")
    if ementa:
        fm.append(f"ementa: {yaml_str(ementa)}")
    fm.append(f"source: {yaml_str(src)}")
    if src != e["url"]:
        fm.append(f"source_original_page: {yaml_str(e['url'])}")
    fm.append(f"text_version: {'compiled (texto compilado)' if compiled else 'Planalto page (updated in place)'}")
    fm.append(f"struck_through_removed: {parsed['struck']}")
    fm.append(f"retrieved: {TODAY}")
    fm.append("---")

    md = fm + ["", f"# {title}", ""]
    if ptitle and kind != "constituicao":
        md += [f"**{ptitle}**", ""]
    if ementa:
        md += [f"*{P.escape(ementa)}*", ""]
    if notes:
        for n in notes:
            md.append(f"> {n}")
            md.append(">")
        md.pop()
        md.append("")
    for l in lines_body:
        md.append(l)
        md.append("")
    text = "\n".join(md).rstrip() + "\n"
    rel = target_path(e, None)
    path = os.path.join(out_root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return {"url": e["url"], "path": rel, "kind": kind, "status": status, "compiled": compiled,
            "struck": parsed["struck"], "bytes": len(text.encode()), "date": e.get("date")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kinds", default="")
    ap.add_argument("--out", default=REPO)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--years", default="", help="e.g. 2004-2026: only acts dated in this range")
    a = ap.parse_args()
    idx = json.load(open(os.path.join(net.RAW, "index.json")))
    code_urls = {e["url"].lower() for e in idx if e["kind"] == "codigo"}
    todo = [e for e in idx if selected(e)]
    if a.kinds:
        ks = set(a.kinds.split(","))
        todo = [e for e in todo if e["kind"] in ks]
    if a.years:
        y0, y1 = a.years.split("-")
        todo = [e for e in todo if y0 <= (e.get("date") or "0000")[:4] <= y1]
    # disambiguate duplicate target paths (same number & year listed twice with different pages)
    seen = {}
    for e in todo:
        p = target_path(e, None)
        if p in seen:
            e["number"] = e["number"] + "-" + str(sum(1 for q in seen if q.startswith(p[:-3])) + 1)
        seen[target_path(e, None)] = e
    report = []
    with cf.ProcessPoolExecutor(a.workers) as ex:
        for r in ex.map(convert_one, todo, [code_urls] * len(todo), [a.out] * len(todo), chunksize=8):
            if r:
                report.append(r)
                if r.get("error"):
                    print("ERROR", r, file=sys.stderr)
    rp = os.path.join(net.RAW, "convert_report.json")
    old = []
    if a.kinds and os.path.exists(rp):
        old = [r for r in json.load(open(rp)) if r.get("kind") not in set(a.kinds.split(","))]
    with open(rp, "w") as f:
        json.dump(old + report, f, ensure_ascii=False, indent=0)
    print(f"converted {sum(1 for r in report if not r.get('error'))}, errors {sum(1 for r in report if r.get('error'))}")


if __name__ == "__main__":
    main()
