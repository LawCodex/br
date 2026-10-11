"""Polite cached HTTP client for planalto.gov.br and the Senado open-data API.

Every response body is cached gzip-compressed under RAW/cache/ (keyed by URL) so that re-runs
never re-download. Planalto's web application firewall drops requests whose User-Agent does
not look like a browser, so the UA is a Mozilla-compatible string that still identifies LawCodex.
"""
import gzip
import hashlib
import os
import random
import re
import threading
import time

import requests

UA = "Mozilla/5.0 (compatible; LawCodex/1.0; +https://github.com/LawCodex)"
RAW = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "_raw", "br"))
CACHE = os.path.join(RAW, "cache")

_local = threading.local()
_sem = threading.Semaphore(4)  # max concurrent requests


def session():
    s = getattr(_local, "s", None)
    if s is None:
        s = requests.Session()
        s.headers["User-Agent"] = UA
        _local.s = s
    return s


def cache_path(url):
    h = hashlib.sha1(url.encode()).hexdigest()
    return os.path.join(CACHE, h[:2], h + ".gz")


class NotFound(Exception):
    pass


def canonical(url):
    """Planalto answers every mixed-case path with a 301 to the lower-case path: request the
    lower-case URL directly to save a round trip."""
    m = re.match(r"^https?://(www\.)?planalto\.gov\.br(/.*)$", url, re.I)
    if m:
        return "https://www.planalto.gov.br" + m.group(2).lower()
    return url


def get(url, refresh=False, retries=6, accept=None):
    """Return the raw bytes of URL (cached). Raises NotFound on 404/403."""
    legacy = cache_path(url)
    url = canonical(url)
    p = cache_path(url)
    if not refresh and not os.path.exists(p) and os.path.exists(legacy):
        p = legacy
    if not refresh and os.path.exists(p):
        with gzip.open(p, "rb") as f:
            data = f.read()
        if data == b"__404__":
            raise NotFound(url)
        return data
    last = None
    for i in range(retries):
        try:
            with _sem:
                headers = {"Accept": accept} if accept else {}
                r = session().get(url, timeout=120, headers=headers)
                time.sleep(0.15)
            if r.status_code in (403, 404):
                # Planalto answers missing pages with 404 (and directory listings with 403)
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with gzip.open(p, "wb") as f:
                    f.write(b"__404__")
                raise NotFound(url)
            if r.status_code >= 500 or r.status_code == 429:
                raise requests.HTTPError(f"HTTP {r.status_code}")
            r.raise_for_status()
            data = r.content
            os.makedirs(os.path.dirname(p), exist_ok=True)
            tmp = p + f".{os.getpid()}.{threading.get_ident()}.tmp"
            with gzip.open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, p)
            return data
        except NotFound:
            raise
        except Exception as e:  # network error, 5xx, WAF reset
            last = e
            time.sleep(min(60, 2 ** i + random.random()))
    raise RuntimeError(f"failed {url}: {last}")


def decode(data):
    """Decode a Planalto HTML page (mostly windows-1252, newer pages UTF-8)."""
    head = data[:4000].lower()
    m = re.search(rb'charset\s*=\s*["\']?([a-z0-9_-]+)', head)
    if m and m.group(1) in (b"utf-8", b"utf8"):
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            pass
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")
