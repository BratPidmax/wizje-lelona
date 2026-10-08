#!/usr/bin/env python3
"""Generator dynamicznej playlisty TVP - ETAP 2B-B (PROTOTYP, poza projektem).

Pipeline:
  oficjalny sitemap TVP -> product_id -> API TVP (Referer) -> aktualny HLS
  -> walidacja master/wariant/segment -> M3U

BEZPIECZENSTWO:
  - w kodzie NIE MA zadnych tokenizowanych URL-i HLS TVP
  - token generuje TVP podczas kazdego wykonania
  - tokeny NIGDY nie trafiaja do logow (maskowane)
  - generator NIE wykonuje git push sam - to osobny, jawny krok (--push)

Fail-safe:
  pobierz -> zweryfikuj -> zapisz do pliku tymczasowego -> sprawdz kompletnosc
  -> dopiero potem (opcjonalnie) commit/push
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import urljoin

# === STAŁE OFICJALNE (bez żadnych tokenów) ===
SITEMAP = "https://vod.tvp.pl/sitemap/tvp-vod/sitemap-lives.xml"
STATIONS = "https://www.tvp.pl/"
API = "https://vod.tvp.pl/api/products/{id}/videos/playlist?platform=BROWSER&videoType=LIVE"
TVP_REF = "https://vod.tvp.pl/"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/91.0.4472.124 Safari/537.36")

SLUG_ALIAS = {"tvp-3-gorzow-wlkp": "tvp-3-gorzow-wielkopolski",
              "belsat": "tv-bielsat"}
SLUG_SPELLING = {
    "tvp-milosc": "TVP Miłość",
    "tvp-muzyka-i-koncerty": "TVP Muzyka i Koncerty",
    "tvp-parlament--sejm": "TVP Parlament Sejm",
    "tvp-parlament--senat": "TVP Parlament Senat",
    "tvp-historia-2": "TVP Historia 2",
    "tvp-abc-2": "TVP ABC 2",
    "tvp-kultura-2": "TVP Kultura 2",
    "final-ligi-mistrzow": "Final Ligi Mistrzów",
    "xix-miedzynarodowy-konkurs-pianistyczny-im-fryderyka-chopina":
        "XIX Międzynarodowy Konkurs Pianistyczny im. Fryderyka Chopina",
}

# Minimalny próg dla SAMEGO TVP (niezależny od globalnego MIN_CHANNELS=200)
MIN_TVP_OK = 25
DEFAULT_OUT = "/tmp/opencode/tvp_m3u_test/tvp-test.m3u"


# ---------------------------------------------------------------- HTTP
def http(url, ref=None, tmo=15, data=None):
    h = {"User-Agent": UA}
    if ref:
        h["Referer"] = ref
    req = urllib.request.Request(url, headers=h, data=data)
    try:
        with urllib.request.urlopen(req, timeout=tmo) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception:
        return 0, b""


def mask(url):
    """Maska tokenu - do logów i raportów. Token siedzi w ścieżce URL-a."""
    if not url:
        return ""
    return re.sub(r"(/token/video/(?:live|vod)/\d+)/\d+/\d+/[^/]+",
                  r"\1/<date>/<session>/<TOKEN>", url)


# ---------------------------------------------------------------- katalog
def build_catalogue():
    st, xml = http(SITEMAP, ref=TVP_REF, tmo=25)
    if st != 200:
        raise SystemExit(f"BLAD: sitemap TVP HTTP {st}")
    pairs = re.findall(r"<loc>https://vod\.tvp\.pl/live,1/([^,]+),(\d+)</loc>",
                       xml.decode("utf-8", "replace"))
    st, page = http(STATIONS, tmo=30)
    names, regs = {}, {}
    if st == 200:
        page = page.decode("utf-8", "replace")
        blk = page[page.find("__stationsData"):]
        blk = blk[:blk.find("</script>")]
        for _key, name, rest in re.findall(
                r'"([A-Z0-9_]+)":\s*\{\s*"name":\s*"([^"]+)"([^}]*)\}', blk):
            u = re.search(r'"url":\s*"([^"]+)"', rest)
            if not u:
                continue
            slug = u.group(1).split("/")[-1]
            names[slug] = re.sub(r"\\u([0-9a-fA-F]{4})",
                                 lambda m: chr(int(m.group(1), 16)), name)
            regs[slug] = '"regional": true' in rest
    cat = {}
    for slug, pid in pairs:
        canon = SLUG_ALIAS.get(slug, slug)
        if canon in names:
            cat[pid] = {"id": pid, "slug": slug, "name": names[canon],
                        "regional": regs.get(canon, False), "name_source": "stationsData"}
        elif slug in SLUG_SPELLING:
            cat[pid] = {"id": pid, "slug": slug, "name": SLUG_SPELLING[slug],
                        "regional": False, "name_source": "slug+suffix"}
        else:
            cat[pid] = {"id": pid, "slug": slug,
                        "name": re.sub(r"^(Tvp)\b", "TVP", slug.replace("-", " ").title()),
                        "regional": slug.startswith("tvp-3-"), "name_source": "slug"}
    return cat


# ---------------------------------------------------------------- HLS
def parse_variants(t):
    out, pend = [], False
    for ln in t.splitlines():
        s = ln.strip()
        if not s:
            continue
        if s.startswith("#EXT-X-I-FRAME-STREAM-INF"):
            pend = False
            continue
        if s.startswith("#EXT-X-STREAM-INF"):
            pend = True
            continue
        if s.startswith("#"):
            continue
        if pend:
            out.append(s)
            pend = False
    return out


def parse_segments(t):
    return [l.strip() for l in t.splitlines()
            if l.strip() and not l.strip().startswith("#")]


def resolve_and_verify(product_id, timeout=15):
    """Pełna walidacja. Zwraca (ok, url, opis)."""
    st, body = http(API.format(id=product_id), ref=TVP_REF, tmo=timeout)
    if st == 0:
        return False, None, "timeout API"
    if st != 200:
        return False, None, f"API HTTP {st}"
    try:
        data = json.loads(body.decode("utf-8", "replace"))
    except Exception:
        return False, None, "API nie-JSON"
    hls = (data.get("sources") or {}).get("HLS") or []
    if not hls or not hls[0].get("src"):
        return False, None, "brak HLS"
    master = urljoin(API.format(id=product_id), hls[0]["src"])

    st, b = http(master, ref=TVP_REF, tmo=timeout)
    if st != 200:
        return False, None, f"manifest HTTP {st}"
    text = b.decode("utf-8", "replace")
    if not text.lstrip().startswith("#EXTM3U"):
        return False, None, "manifest nie #EXTM3U"
    cur = master
    for _ in range(3):
        vs = parse_variants(text)
        if not vs:
            break
        child = urljoin(cur, vs[0])
        st2, b2 = http(child, ref=TVP_REF, tmo=timeout)
        if st2 != 200:
            return False, None, f"wariant HTTP {st2}"
        t2 = b2.decode("utf-8", "replace")
        if not t2.lstrip().startswith("#EXTM3U"):
            return False, None, "wariant nie #EXTM3U"
        cur, text = child, t2
    segs = parse_segments(text)
    if not segs:
        return False, None, "brak segmentów"
    seg = urljoin(cur, segs[0])
    st3, _ = http(seg, ref=TVP_REF, tmo=timeout)
    if st3 not in (200, 206):
        return False, None, f"segment HTTP {st3}"
    return True, master, f"OK seg={st3} n={len(segs)}"


def verify_later(url, timeout=12):
    """Ponowna kontrola istniejącego URL-a (do testu starzenia tokenu)."""
    st, b = http(url, ref=TVP_REF, tmo=timeout)
    if st != 200:
        return False, f"manifest HTTP {st}"
    text = b.decode("utf-8", "replace")
    if not text.lstrip().startswith("#EXTM3U"):
        return False, "manifest nie #EXTM3U"
    cur = url
    for _ in range(3):
        vs = parse_variants(text)
        if not vs:
            break
        child = urljoin(cur, vs[0])
        st2, b2 = http(child, ref=TVP_REF, tmo=timeout)
        if st2 != 200:
            return False, f"wariant HTTP {st2}"
        cur, text = child, b2.decode("utf-8", "replace")
    segs = parse_segments(text)
    if not segs:
        return False, "brak segmentów"
    st3, _ = http(urljoin(cur, segs[0]), ref=TVP_REF, tmo=timeout)
    return (st3 in (200, 206)), f"segment HTTP {st3}"


# ---------------------------------------------------------------- M3U
def build_m3u(rows):
    now = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    out = [f"#EXTM3U",
           f"# Wizje Lelona - TVP - dynamiczna playlista (ETAP 2B-B, branch testowy)",
           f"# Wygenerowano: {now}",
           f"# Kanaly: {len(rows)} | zrodlo: oficjalne API vod.tvp.pl",
           f"# URL-e sa tokenizowane i krotkotrwale - nie edytuj recznie, generuj ponownie",
           f""]
    for r in sorted(rows, key=lambda x: (not x["regional"], x["name"])):
        safe = r["name"].replace('"', "'")
        out.append(f'#EXTINF:-1 tvg-id="{r["id"]}" tvg-name="{safe}" '
                   f'group-title="TVP",{r["name"]}')
        out.append(r["url"])
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--min-ok", type=int, default=MIN_TVP_OK)
    ap.add_argument("--no-verify", action="store_true",
                    help="pomija pobieranie segmentu (szybki podglad)")
    a = ap.parse_args()

    print("=" * 72)
    print("GENERATOR PLAYLISTY TVP - ETAP 2B-B (prototyp)")
    print("=" * 72)
    cat = build_catalogue()
    reg = sum(1 for v in cat.values() if v["regional"])
    print(f"[1] Oficjalny katalog TVP : {len(cat)} produktow LIVE "
          f"({reg} regionalnych)")

    results = []

    def job(pid):
        info = cat[pid]
        ok, url, note = resolve_and_verify(pid)
        return {"id": pid, "name": info["name"], "regional": info["regional"],
                "slug": info["slug"], "ok": ok, "url": url, "note": note}

    with ThreadPoolExecutor(a.workers) as ex:
        results = list(ex.map(job, cat.keys()))

    good = [r for r in results if r["ok"]]
    bad = [r for r in results if not r["ok"]]
    print(f"[2] Zweryfikowanych OK    : {len(good)}")
    print(f"[3] Odrzuconych           : {len(bad)}")
    from collections import Counter
    print("    powody: " + ", ".join(f"{k}={v}" for k, v in
                                    Counter(r["note"].split()[0] for r in bad).most_common()))
    reg_ok = [r for r in good if r["regional"]]
    print(f"[4] Krajowych OK          : {len(good) - len(reg_ok)}")
    print(f"[5] Regionalnych OK       : {len(reg_ok)}")

    if len(good) < a.min_ok:
        print(f"\n⛔ STOP: tylko {len(good)} dzialajacych kanalow TVP "
              f"(minimum {a.min_ok}). NIE zapisuje, NIE pushuje.")
        return 2

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    # fail-safe: najpierw plik tymczasowy, potem atomowy rename
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(a.out), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(build_m3u(good))
    n = sum(1 for ln in open(tmp, encoding="utf-8") if ln.startswith("#EXTINF"))
    assert n == len(good), f"niespojnosc: {n} != {len(good)}"
    os.replace(tmp, a.out)
    print(f"[6] Zapisano              : {a.out} ({n} pozycji)")
    print("\nKatalog zweryfikowanych kanalow:")
    for r in sorted(good, key=lambda x: (not x["regional"], x["name"])):
        print(f"    {r['id']:>8}  {r['name']:44} {'TVP3 regionalny' if r['regional'] else ''}")
    print("\nOdrzucone:")
    for r in sorted(bad, key=lambda x: x["name"]):
        print(f"    {r['id']:>8}  {r['name'][:36]:38} {r['note']}")
    meta = {"generated": datetime.now(timezone.utc).isoformat(),
            "found": len(cat), "ok": len(good), "rejected": len(bad),
            "regional_ok": len(reg_ok), "rows": [
                {"id": r["id"], "name": r["name"], "regional": r["regional"]}
                for r in good]}
    json.dump(meta, open(os.path.join(os.path.dirname(a.out), "run_meta.json"), "w"),
              ensure_ascii=False, indent=1)
    print(f"\n[7] Raport: {os.path.join(os.path.dirname(a.out), 'run_meta.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())