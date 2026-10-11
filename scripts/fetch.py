#!/usr/bin/env python3
"""Download every norm page listed in RAW/index.json (see enumerate_norms.py), plus its
"Texto compilado" (consolidated) page when Planalto provides one. Pages are cached in
RAW/cache/ (gzip), so the script can be interrupted and re-run.

Usage: python scripts/fetch.py [--workers 4] [--kinds lei,del,...]
"""
import argparse
import concurrent.futures as cf
import json
import os
import sys
import threading
from urllib.parse import urljoin

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import net  # noqa: E402
from select_norms import compiled_url, selected  # noqa: E402


def work(e):
    try:
        html = net.decode(net.get(e["url"]))
    except net.NotFound:
        return "404"
    cu = compiled_url(e["url"], html)
    if cu:
        try:
            net.get(cu)
            return "compiled"
        except net.NotFound:
            return "compiled-404"
    return "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--kinds", default="")
    a = ap.parse_args()
    idx = json.load(open(os.path.join(net.RAW, "index.json")))
    todo = [e for e in idx if selected(e)]
    if a.kinds:
        ks = set(a.kinds.split(","))
        todo = [e for e in todo if e["kind"] in ks]
    lock = threading.Lock()
    stats = {}
    with cf.ThreadPoolExecutor(min(a.workers, 4)) as ex:
        futs = {ex.submit(work, e): e for e in todo}
        for i, f in enumerate(cf.as_completed(futs), 1):
            e = futs[f]
            try:
                r = f.result()
            except Exception as ex_:  # keep going; re-run to retry
                r = "error"
                print(f"ERROR {e['url']}: {ex_}", file=sys.stderr, flush=True)
            with lock:
                stats[r] = stats.get(r, 0) + 1
            if r == "404":
                print(f"404 {e['kind']} {e['number']} {e['url']}", file=sys.stderr, flush=True)
            if i % 200 == 0:
                print(f"{i}/{len(todo)} {stats}", flush=True)
    print(f"done {len(todo)} {stats}", flush=True)


if __name__ == "__main__":
    main()
