"""Selection rules shared by fetch.py and convert.py."""
import datetime
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup


def selected(e):
    """Which index entries are converted.

    Everything listed by Planalto is taken, except medidas provisórias: only those that
    Planalto's tables mark as still pending ("Em Tramitação") are in force — that includes
    the pre-2001 MPs kept in force indefinitely by art. 2 of Constitutional Amendment 32/2001.
    Converted, rejected, lapsed or revoked MPs are skipped (their content lives on in the
    conversion law, if any)."""
    if e["kind"] != "mpv":
        return True
    s = (e.get("situacao") or "") + " " + (e.get("ementa") or "")[-80:]
    if re.search(r"revogad|convertid|rejeitad|encerrad|prejudicad|sem efic", e.get("situacao") or "", re.I):
        return False
    if not re.search(r"em\s+tramita", s, re.I):
        return False
    # Post-EC 32 MPs lapse after at most 120 days (plus parliamentary recess); a few MPs from
    # 2020 are still labelled "Em Tramitação" in Planalto's table although they lapsed long ago.
    d = e.get("date") or ""
    if d >= "2001-09-12" and d < (datetime.date.today() - datetime.timedelta(days=240)).isoformat():
        return False
    return True


def _stem(u):
    b = u.split("#")[0].rstrip("/").split("/")[-1].lower()
    return re.sub(r"\.html?$", "", b)


def _norm(u):
    u = u.split("#")[0].strip().replace("\\", "/")
    return re.sub(r"^https?://(www\.)?planalto\.gov\.br/", "https://www.planalto.gov.br/", u, flags=re.I)


def compiled_url(page_url, html):
    """URL of the 'Texto compilado' version linked from a Planalto page, if any."""
    soup = BeautifulSoup(html[:200000], "lxml")  # the link is always in the header
    stem = _stem(page_url)
    for a in soup.find_all("a"):
        h = (a.get("href") or "").strip()
        if not h or h.startswith("#") or h.lower().startswith("mailto"):
            continue
        t = re.sub(r"\s+", " ", a.get_text(" ")).strip().lower()
        hs = _stem(h)
        if not re.search(r"\.html?($|#)", h, re.I):
            continue
        if "compilad" in hs and (hs.startswith(stem) or stem.startswith(hs.replace("compilado", "").replace("compilada", ""))):
            return _norm(urljoin(page_url, h))
        if t.startswith("texto compilado") and "compilad" in hs:
            return _norm(urljoin(page_url, h))
    return None
