"""Convert a Planalto (ccivil_03) legislation HTML page to Markdown.

Planalto pages are hand-made (FrontPage/Word) HTML with no semantic markup: every provision is a
<p>. Superseded wording is kept on the page struck through (<strike>, <s>, <del> or CSS
line-through) next to the current wording. This module drops struck-through text so that the
result is the text currently in force, keeps Planalto's inline annotations such as
"(Redação dada pela Lei nº ...)" or "(Revogado pela Lei nº ...)", and maps the structural
divisions (Parte, Livro, Título, Capítulo, Seção, Subseção) and articles to Markdown headings.
"""
import re

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

BLOCK = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote", "center", "pre",
         "table", "ul", "ol", "dl", "dd", "dt", "tr", "td", "th", "form", "body", "html", "address"}
STRIKE_TAGS = {"strike", "s", "del"}

ROMAN = r"[IVXLCDM]+"
ORD = r"(?:\d+|" + ROMAN + r"|[ÚU]NIC[OA]|PRIMEIR[OA]|SEGUND[OA]|TERCEIR[OA]|QUART[OA]|QUINT[OA]|SEXT[OA]|S[ÉE]TIM[OA]|OITAV[OA]|NON[OA]|D[ÉE]CIM[OA]|GERAL|ESPECIAL|PRELIMINAR)"
STRUCT = [
    ("parte", re.compile(r"^PARTE\s+(" + ORD + r"|GERAL|ESPECIAL)\b", re.I)),
    ("livro", re.compile(r"^LIVRO\s+(" + ORD + r"|COMPLEMENTAR)\b", re.I)),
    ("titulo", re.compile(r"^T[ÍI]TULO\s+" + ORD + r"\b", re.I)),
    ("capitulo", re.compile(r"^CAP[ÍI]TULO\s+" + ORD + r"[-A-Z]*\b", re.I)),
    ("secao", re.compile(r"^SE[ÇC][ÃA]O\s+" + ORD + r"[-A-Z]*\b", re.I)),
    ("subsecao", re.compile(r"^SUBSE[ÇC][ÃA]O\s+" + ORD + r"[-A-Z]*\b", re.I)),
]
STRUCT_ORDER = ["anexo", "parte", "livro", "titulo", "capitulo", "secao", "subsecao"]
TOP_RE = re.compile(r"^(ATO DAS DISPOSI[ÇC][ÕO]ES CONSTITUCIONAIS TRANSIT[ÓO]RIAS|ANEXO(\s+[\wºª°.-]+)?|PRE[ÂA]MBULO)\s*$", re.I)
ART_RE = re.compile(r"^(Art(?:igo)?\.?\s*(\d+(?:\.\d{3})*)\s*(?:\.?\s*[º°o](?![a-zà-ú])|\.(?!\d))?(?:\s?-\s?(?-i:[A-Z]{1,2})(?![a-zà-ú]))?)\s*[.:\-–—]?\s*", re.I)
QUOTE_START = re.compile(r"^[\"“”'‘’«]")
QUOTE_END = re.compile(r"([\"”’»]\s*(\((NR|AC)\))?|\((NR|AC)\)|\(NR\s*\))\s*(\(.{0,200}\))?\s*[.;]?$")
AMEND_TRIGGER = re.compile(r"(reda[çc][ãa]o|vigorar|acrescid|acrescentad|inserid|aditad|altera[çc][õo]es|"
                           r"seguintes?\s+(art|disposi|par[áa]graf|inci|al[íi]nea|§|item|itens|anexo|cap[íi]tul|se[çc]))", re.I)
LABEL_RE = re.compile(r"^\s*(Art(?:igo)?\.?\s*\d+(?:\.\d{3})*\s*[º°o]?(?:\s*-\s*[A-Z]{1,3}\b)?\.?|§\s*\d+[º°o]?(?:\s*-\s*[A-Z])?|Par[áa]grafo [úu]nico\.?|" + ROMAN + r"(?:\s*-\s*[A-Z])?\s*[-–—]|[a-z]\))", re.I)
REVOKED_RE = re.compile(r"(revogad[oa]s?|tornad[oa] sem efeito|sem efic[áa]cia|vig[êe]ncia encerrada|rejeitad[oa]|caducou|perdeu a efic[áa]cia|suspens[oa] (a execu|pela resol))", re.I)


def clean(t):
    t = re.sub(r"\s*\x01", "", t)
    t = t.replace("\xa0", " ").replace("​", "").replace("\r", " ").replace("\t", " ")
    t = re.sub(r"[ \n]+", " ", t)
    return t.strip()


def is_struck(el):
    if el.name in STRIKE_TAGS:
        return True
    st = (el.get("style") or "").lower().replace(" ", "")
    return "line-through" in st


def remove_struck(soup):
    """Remove struck-through elements. If a whole paragraph is struck except for a trailing
    annotation such as '(Revogado pela Lei nº ...)', keep the provision label (e.g. 'Art. 7º')
    in front of the annotation. Returns the number of removed elements."""
    n = 0
    for el in list(soup.find_all(is_struck)):
        if el.parent is None:  # already removed with an ancestor
            continue
        txt = clean(el.get_text(" "))
        # find enclosing block
        blk = el.parent
        while blk is not None and blk.name not in BLOCK:
            blk = blk.parent
        m = LABEL_RE.match(txt)
        label = m.group(1) if m else None
        el.replace_with(" ")
        n += 1
        if label and blk is not None:
            rest = clean(blk.get_text(" "))
            if rest and not LABEL_RE.match(rest) and re.match(r"^[\(\[]", rest):
                # e.g. "(Revogado pela Lei nº ...)": prefix the provision label once
                first = blk.find(string=lambda s: s.strip())
                if first is not None and not getattr(blk, "_labelled", False):
                    first.replace_with(label + " " + first.lstrip())
                    blk._labelled = True
    return n


def table_to_md(tbl):
    rows = []
    complex_ = False
    for tr in tbl.find_all("tr"):
        if tr.find_parent("table") is not tbl:
            continue
        cells = tr.find_all(["td", "th"], recursive=False)
        row = []
        for c in cells:
            if c.get("colspan") not in (None, "1") or c.get("rowspan") not in (None, "1") or c.find("table"):
                complex_ = True
            row.append(clean(c.get_text(" ")).replace("|", "\\|"))
        if any(row):
            rows.append(row)
    if not rows:
        return ""
    if complex_:
        # keep as minimal HTML
        out = ["<table>"]
        for tr in tbl.find_all("tr"):
            if tr.find_parent("table") is not tbl:
                continue
            cs = []
            for c in tr.find_all(["td", "th"], recursive=False):
                attrs = "".join(f' {a}="{c.get(a)}"' for a in ("colspan", "rowspan") if c.get(a) not in (None, "1"))
                txt = clean(c.get_text(" ")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                cs.append(f"<td{attrs}>{txt}</td>")
            if cs:
                out.append("<tr>" + "".join(cs) + "</tr>")
        out.append("</table>")
        return "\n".join(out)
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    if width == 1:
        return "\n\n".join(r[0] for r in rows if r[0])
    lines = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * width]
    for r in rows[1:]:
        lines.append("| " + " | ".join(r) + " |")
    return "\n".join(lines)


def is_layout_table(tbl):
    txt = tbl.get_text(" ")
    if re.search(r"(^|\s)Art\.\s*\d", txt) and len(tbl.find_all("p")) > 3:
        return True
    if len(tbl.find_all("table")) > 0 and len(txt) > 3000:
        return True
    return False


def blocks(root):
    """Yield ('p', text) / ('table', md) items in document order."""
    buf = []
    state = {"art": False}

    def flush():
        t = clean("".join(buf))
        buf.clear()
        if t:
            if not state["art"] and ART_RE.match(t):
                state["art"] = True
            return ("p", t)
        return None

    def walk(node):
        for ch in list(node.children):
            if isinstance(ch, Comment):
                continue
            if isinstance(ch, NavigableString):
                buf.append(str(ch))
                continue
            if not isinstance(ch, Tag):
                continue
            name = ch.name
            if name in ("script", "style", "head", "title", "meta", "link", "img", "map", "area", "object", "iframe", "noscript"):
                continue
            if name == "br":
                r = flush()
                if r:
                    yield r
                continue
            if name == "table":
                r = flush()
                if r:
                    yield r
                small_header = (not state["art"] and len(ch.find_all("tr")) <= 3
                                and len(ch.get_text(" ")) < 4000)
                if small_header or is_layout_table(ch):
                    yield from walk(ch)
                else:
                    md = table_to_md(ch)
                    if md:
                        yield ("table", md)
                continue
            if name in BLOCK:
                r = flush()
                if r:
                    yield r
                yield from walk(ch)
                r = flush()
                if r:
                    yield r
            else:
                yield from walk(ch)

    yield from walk(root)
    r = flush()
    if r:
        yield r


def find_compiled_link(html_soup):
    for a in html_soup.find_all("a"):
        h = a.get("href") or ""
        t = clean(a.get_text(" ")).lower()
        if "compilad" in h.lower() or t in ("texto compilado", "texto compilado."):
            if h.lower().endswith((".htm", ".html")) or ".htm#" in h.lower():
                return h.split("#")[0]
    return None


def parse(html):
    """Return dict(title, notes, ementa, body_items, struck) from a Planalto page."""
    # Planalto pages often contain stray </body></html> (or several <html>/<body>) in the middle
    # of the text: drop those tags so that the parser keeps the whole document together.
    html = re.sub(r"<head\b.*?</head\s*>", " ", html, flags=re.I | re.S)
    html = re.sub(r"</?(html|body)\b[^>]*>", " ", html, flags=re.I)
    soup = BeautifulSoup("<html><body>" + html + "</body></html>", "lxml")
    # ordinal superscripts: "Art. 1<sup>o</sup>" -> "Art. 1º"
    for sup in soup.find_all("sup"):
        tx = sup.get_text().strip()
        if tx in ("o", "º", "°", "os", "a", "ª", "as"):
            sup.replace_with("\x01" + ("ª" if tx[0] in "aª" else "º") + (tx[1:] if len(tx) > 1 else ""))
    for t in soup(["script", "style", "head"]):
        t.decompose()
    for c in soup.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
    struck = remove_struck(soup)
    body = soup.body or soup
    # drop the Planalto masthead table (Brasão + "Presidência da República")
    for tbl in body.find_all("table"):
        tx = clean(tbl.get_text(" "))
        if re.search(r"Presid[êe]ncia\s+da\s+Rep[úu]blica", tx) and len(tx) < 300:
            tbl.decompose()
            break
    items = list(blocks(body))
    return {"items": items, "struck": struck}


TITLE_RE = re.compile(r"^(LEI|DECRETO|EMENDA|MEDIDA|CONSTITUI|C[ÓO]DIGO|ATO)\b.*\b(1[89]\d\d|20\d\d)\s*\.?$", re.I)
ENACT_RE = re.compile(r"^(O\s+PRESIDENTE\s+DA\s+REP|A\s+PRESIDENTA\s+DA\s+REP|O\s+VICE-PRESIDENTE|AS\s+MESAS\s+DA|O\s+CONGRESSO\s+NACIONAL|N[ÓO]S,?\s+(OS\s+)?REPRESENTANTES|O\s+PRESIDENTE\s+DO\s+CONGRESSO|OS\s+MINISTROS|A\s+JUNTA|O\s+CHEFE\s+DO\s+GOVERNO|D\.\s*PEDRO|DOM\s+PEDRO|A\s+PRINCESA|O\s+REGENTE|A\s+REGÊNCIA|O\s+PRESIDENTE\s+DOS\s+ESTADOS|O\s+PRESIDENTE\s+DA\s+REPUBLICA|O\s+GOVERNO\s+PROVIS)", re.I)
HEADER_NOISE = re.compile(r"^(Presid[êe]ncia\s+da\s+Rep[úu]blica|Casa\s+Civil|Subchefia\s+para\s+Assuntos\s+Jur[íi]dicos|Secretaria(\s+Especial)?\s+para\s+Assuntos\s+Jur[íi]dicos|Secretaria-Geral|Texto\s+para\s+impress[ãa]o|Texto\s+compilado|Vig[êe]ncia|Mensagem\s+de\s+veto|Regulamento|Convers[ãa]o|Exposi[çc][ãa]o\s+de\s+motivos|Produ[çc][ãa]o\s+de\s+efeito|Promulga[çc][ãa]o\s+partes\s+vetadas|Emendas\s+Constitucionais(\s+de\s+Revis[ãa]o)?|[ÍI]ndice\s+Tem[áa]tico|Atos\s+decorrentes\s+do\s+disposto.*|Ato\s+das\s+Disposi[çc][õo]es\s+Constitucionais\s+Transit[óo]rias)[\s.()]*$", re.I)


def _key(t):
    return re.sub(r"[^a-z0-9]", "", __import__("unicodedata").normalize("NFKD", t.lower()).encode("ascii", "ignore").decode())


NOTE_RE = re.compile(r"^(\(|\[|revogad|vide\b|vig[êe]ncia|regulamento|convers|produ[çc][ãa]o|texto|mensagem|promulga|"
                     r"retifica|republica|convertid|rejeitad|sem efic|tornad|suspens|declarad|ver\b|v\.\s)", re.I)


def split_header(items, known_ementa=None):
    """Split items into (title, notes, ementa, body).

    The header is everything before the enacting formula ('O PRESIDENTE DA REPÚBLICA...',
    'As Mesas da Câmara...') or the first article/structural division."""
    idx = None
    for i, (k, t) in enumerate(items[:80]):
        if k != "p":
            continue
        if ENACT_RE.match(t) or ART_RE.match(t) or any(r.match(t) for _, r in STRUCT) or re.match(r"^PRE[ÂA]MBULO\s*$", t, re.I):
            idx = i
            break
    if idx is None:
        idx = 0
    head, body = items[:idx], items[idx:]
    title, notes, ementa = None, [], None
    texts = [t for k, t in head if k == "p"]
    for t in texts:
        if title is None and TITLE_RE.match(t) and len(t) < 200:
            title = t.rstrip(".").strip()
    rest = [t for t in texts if t.rstrip(".").strip() != title and not HEADER_NOISE.match(t)]
    ke = _key(known_ementa or "")[:60]
    if ke:
        for t in rest:
            k = _key(t)
            if k and (ke[:40] in k or k[:40] in ke):
                ementa = t
                break
    if ementa is None:
        # the last text in the header that is not an annotation
        for t in reversed(rest):
            if not NOTE_RE.match(t) and len(t) > 8:
                ementa = t
                break
    notes = [t for t in rest if t != ementa]
    return title, notes, ementa, body


def classify(t):
    if re.match(r"^P\s?A\s?R\s?T\s?E\s+(G\s?E\s?R\s?A\s?L|E\s?S\s?P\s?E\s?C\s?I\s?A\s?L)\b", t):
        return "parte"
    if TOP_RE.match(t):
        return "anexo"
    for k, r in STRUCT:
        if r.match(t):
            return k
    return None


def to_markdown_body(body, title_level=1):
    """Render body items to Markdown lines with heading hierarchy."""
    # merge structural label with following name line ("CAPÍTULO I" + "DISPOSIÇÕES GERAIS")
    merged = []
    i = 0
    while i < len(body):
        k, t = body[i]
        if k == "p":
            c = classify(t)
            if c and i + 1 < len(body) and body[i + 1][0] == "p":
                nxt = body[i + 1][1]
                label_only = (c == "anexo") or re.fullmatch(r"\S+\s+\S+(\s*\(.*\))?\.?", t) is not None
                if (label_only and not classify(nxt) and not ART_RE.match(nxt) and len(nxt) < 250
                        and not re.search(r"[;:]$", nxt) and not LABEL_RE.match(nxt) and not nxt.startswith("(")):
                    merged.append(("h", c, f"{t} — {nxt}" if not t.endswith(("-", "–", "—")) else f"{t} {nxt}"))
                    i += 2
                    continue
            if c:
                merged.append(("h", c, t))
                i += 1
                continue
        merged.append((k, None, t))
        i += 1

    present = [s for s in STRUCT_ORDER[1:] if any(m[0] == "h" and m[1] == s for m in merged)]
    level = {}
    lv = title_level + 1
    for s in present:
        level[s] = min(lv, 6)
        lv += 1
    # annexes / ADCT / preamble sit at the level of the top division
    level["anexo"] = title_level + 1
    art_level = lv if lv <= 6 else None
    has_art = any(m[0] == "p" and ART_RE.match(m[2]) for m in merged)

    out = []
    quoted = False      # inside text quoted by an amending provision
    last_own = 0        # number of the act's own last article
    for kind, c, t in merged:
        if kind == "h":
            t2 = re.sub(r"\s", "", t)
            if re.fullmatch(r"(\S ){3,}\S", t) and t2.upper() in ("PARTEGERAL", "PARTEESPECIAL"):
                t = t2[:5] + " " + t2[5:]
            if quoted:
                out.append(escape(t))
                continue
            out.append("#" * level[c] + " " + t)
            continue
        if kind == "table":
            out.append(t)
            continue
        m = ART_RE.match(t) if has_art else None
        own = False
        if m and not QUOTE_START.match(t):
            n = int(m.group(2).replace(".", ""))
            if not quoted or n in (last_own + 1, last_own + 2) or (n == last_own and "-" in m.group(1)):
                own = True
                quoted = False
                last_own = n
        if own:
            label = clean(m.group(1))
            rest = t[m.end():].strip()
            if art_level:
                out.append("#" * art_level + " " + label)
                if rest:
                    out.append(escape(rest))
            else:
                out.append(f"**{label}** " + escape(rest))
            if rest.endswith(":") and AMEND_TRIGGER.search(rest):
                quoted = True
            continue
        if not quoted and t.endswith(":") and AMEND_TRIGGER.search(t) and not ART_RE.match(t):
            quoted = True   # e.g. "§ 1º O art. 5º passa a vigorar com a seguinte redação:"
        out.append(escape(t))
        if quoted and QUOTE_END.search(t):
            quoted = False
    return out


def escape(t):
    # avoid accidental Markdown structures at line start
    if re.match(r"^(#|>|\d+\.\s|[-+]\s|[*_]|=+$|-{3,}$)", t):
        t = "\\" + t
    return t
