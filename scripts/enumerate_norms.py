#!/usr/bin/env python3
"""Enumerate federal norms from the Planalto (ccivil_03) index tables ("quadros").

Writes RAW/index.json: a list of entries
  {kind, number, date, url, ementa, situacao, index}
kind is one of: constituicao, emc, ecr, codigo, lcp, lei, ldl, del, mpv, lim

Usage: python scripts/enumerate_norms.py [--refresh]
"""
import json
import os
import re
import sys
from urllib.parse import urljoin

from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import net  # noqa: E402

B = "https://www.planalto.gov.br/ccivil_03/"
REFRESH = "--refresh" in sys.argv


def soup(url):
    return BeautifulSoup(net.decode(net.get(url, refresh=REFRESH)), "lxml")


def norm_url(u):
    """Canonical absolute URL: https, www host, fragment stripped."""
    u = u.split("#")[0].strip()
    u = re.sub(r"^https?://(www\.)?planalto\.gov\.br/", "https://www.planalto.gov.br/", u, flags=re.I)
    return u.replace("\\", "/")


def clean(t):
    return re.sub(r"\s+", " ", t.replace("\xa0", " ")).strip()


DATE_RE = re.compile(r"(\d{1,2})\s*[º°o]?\s*[./]\s*(\d{1,2})\s*[./]\s*(\d{2,4})")
MONTHS = {m: i + 1 for i, m in enumerate(
    "janeiro fevereiro março abril maio junho julho agosto setembro outubro novembro dezembro".split())}


def parse_date(text, century=1900):
    m = DATE_RE.search(text)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        m = re.search(r"(\d{1,2})\s*[º°o]?\s+de\s+([a-zç]+)\s+de\s+(\d{4})", text, re.I)
        if not m or m.group(2).lower() not in MONTHS:
            return None
        d, mo, y = int(m.group(1)), MONTHS[m.group(2).lower()], int(m.group(3))
    if y < 100:
        y += century
    if not (1 <= mo <= 12 and 1 <= d <= 31):
        return None
    return f"{y:04d}-{mo:02d}-{d:02d}"


NUM_RE = re.compile(r"(\d{1,3}(?:\.\d{3})*(?:-[A-Z0-9]+)?)")


def parse_rows(url, kind, century=1900, link_filter=None):
    """Generic quadro parser: rows whose first cell links to a norm page."""
    s = soup(url)
    out = []
    for tr in s.find_all("tr"):
        tds = tr.find_all("td", recursive=False) or tr.find_all("td")
        if len(tds) < 2:
            continue
        first = tds[0]
        links = [a for a in first.find_all("a") if a.get("href")]
        links = [a for a in links if re.search(r"\.html?$", a["href"].split("#")[0], re.I)
                 and not re.search(r"(mensagem|msg|vep|exm|veto|prorrog|congresso|adc-|apn-)", a["href"], re.I)]
        if link_filter:
            links = [a for a in links if link_filter(a["href"])]
        if not links:
            continue
        a = links[0]
        ftxt = clean(first.get_text(" "))
        # number: first number in the link text (fallback: cell text)
        ltxt = re.sub(r"\s+", "", a.get_text(""))  # quadros split numbers across tags
        ltxt2 = re.sub(r"^(leicomplementar|lei|medidaprovis[óo]ria|decreto-lei|emendaconstitucional)(n[º°o.]*)?", "", ltxt, flags=re.I)
        m = NUM_RE.search(ltxt2) or NUM_RE.search(re.sub(r"\s+", "", ftxt))
        if not m:
            continue
        tnum = m.group(1).replace(".", "")
        base = re.sub(r"\.html?$", "", a["href"].split("#")[0].split("/")[-1], flags=re.I).replace(".", "")
        um = re.search(r"(\d+(?:-\d+)?)", base)
        number = (um.group(1).lstrip("0") if um else "") or tnum.lstrip("0")
        if kind == "lim":
            number = ""
        elif re.fullmatch(re.escape(number.split("-")[0]) + r"(-[A-Z])?", tnum.lstrip("0")):
            number = tnum.lstrip("0")
        elif tnum.lstrip("0") != number:
            print(f"note: {kind} text number {tnum!r} != file name number {number!r} ({a['href']})", file=sys.stderr)
        date = parse_date(re.sub(r"\s+", "", first.get_text("")), century) or parse_date(ftxt, century)
        ementa = clean(tds[1].get_text(" "))
        situacao = clean(tds[2].get_text(" ")) if len(tds) > 2 else ""
        out.append({
            "kind": kind, "number": number, "date": date,
            "url": norm_url(urljoin(url, a["href"])),
            "ementa": ementa, "situacao": situacao, "index": url,
        })
    return out


def links_of(url, pattern):
    s = soup(url)
    res = []
    for a in s.find_all("a"):
        h = a.get("href")
        if h and re.search(pattern, h, re.I):
            u = norm_url(urljoin(url, h))
            if u not in res:
                res.append(u)
    return res


def main():
    entries = []
    # Constitution
    entries.append({"kind": "constituicao", "number": "1988", "date": "1988-10-05",
                    "url": B + "constituicao/constituicao.htm",
                    "ementa": "Constituição da República Federativa do Brasil de 1988", "situacao": "", "index": ""})
    # Constitutional amendments
    entries += parse_rows(B + "constituicao/emendas/emc/quadro_emc.htm", "emc")
    entries += parse_rows(B + "constituicao/Emendas/ECR/quadro_ecr.htm", "ecr")
    # Codes
    s = soup(B + "Codigos/quadro_cod.htm")
    for tr in s.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) != 2:
            continue
        name = clean(tds[0].get_text(" ")).rstrip(".")
        for a in tds[1].find_all("a"):
            h = a.get("href")
            if not h or "codi_Conduta" in h:
                continue
            ltxt = clean(a.get_text(" "))
            nos = re.sub(r"\s+", "", ltxt)
            um = re.search(r"(\d+)", re.sub(r"\.html?$", "", h.split("/")[-1]).replace(".", ""))
            entries.append({"kind": "codigo", "number": um.group(1).lstrip("0") if um else "",
                            "date": parse_date(nos),
                            "url": norm_url(urljoin(B + "Codigos/quadro_cod.htm", h)), "ementa": "", "situacao": "",
                            "index": B + "Codigos/quadro_cod.htm", "code_name": name, "code_ref": ltxt})
    # Leis complementares
    entries += parse_rows(B + "leis/LCP/Quadro_Lcp.htm", "lcp")
    # Leis delegadas
    entries += parse_rows(B + "leis/Ldl/Quadro_LDL.htm", "ldl")
    # Leis ordinárias: per-year index pages
    for u in links_of(B + "leis/_lei-ordinaria.htm", r"(QUADRO/|_Quadro|_quadro|_leis\d{4})"):
        if u.endswith("_Lei-principal.htm"):
            continue
        entries += parse_rows(u, "lei")
    # Leis do Império
    try:
        entries += parse_rows(B + "leis/LIM/_Quadro-LIM.htm", "lim", century=1800)
    except net.NotFound:
        pass
    # Decretos-lei
    for u in links_of(B + "Decreto-Lei/principal_ano.htm", r"_quadro\.htm$"):
        entries += parse_rows(u, "del")
    # Medidas provisórias
    for u in links_of(B + "MPV/Principal.htm", r"Quadro/"):
        entries += parse_rows(u, "mpv", link_filter=lambda h: re.search(r"(mpv|antigas|/\d)", h, re.I))

    # broken links in Planalto's tables (target moved)
    FIX = {B.lower() + "leis/l0556-1850.htm": B + "leis/lim/lim556.htm"}
    for e in entries:
        e["url"] = FIX.get(e["url"].lower(), e["url"])

    # codes: take number/date from the matching law / decree-law entry
    by_url = {e["url"].lower(): e for e in entries if e["kind"] in ("lei", "del")}
    for e in entries:
        if e["kind"] == "codigo":
            m = by_url.get(e["url"].lower())
            if m:
                e["number"], e["date"], e["ementa"] = m["number"], m["date"], m["ementa"]
                e["act_kind"] = m["kind"]
            else:
                e["act_kind"] = "dec" if e["code_ref"].lower().startswith("dec") else "lei"

    # de-duplicate by (kind, url)
    seen, uniq = set(), []
    for e in entries:
        k = (e["kind"], e["url"].lower())
        if k in seen:
            continue
        seen.add(k)
        uniq.append(e)
    with open(os.path.join(net.RAW, "index.json"), "w") as f:
        json.dump(uniq, f, ensure_ascii=False, indent=0)
    from collections import Counter
    print(Counter(e["kind"] for e in uniq))


if __name__ == "__main__":
    main()
