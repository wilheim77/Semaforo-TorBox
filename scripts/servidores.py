"""Descarga la lista de servidores de prueba de TorBox y la guarda en servers.json.

La página no puede leer la API de TorBox desde otro dominio (CORS), así que este
script lo hace desde GitHub Actions y deja el resultado junto a la página.
Para cada fichero de prueba anota su tamaño y si el CDN permite leerlo desde
otra web, que es lo que decide cómo mide la página.
"""
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone

API = "https://api.torbox.app/v1/api/speedtest"
ORIGIN = "https://wilheim77.github.io"
UA = "SemaforoTorBox/1.0 (+https://github.com/wilheim77/Semaforo-TorBox)"


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def items_of(payload):
    data = payload.get("data") if isinstance(payload, dict) else payload
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return list(data.values())
    return []


def find_url(item):
    if not isinstance(item, dict):
        return None
    for k in ("url", "link", "download", "path", "file"):
        v = item.get(k)
        if isinstance(v, str) and v.startswith("http"):
            return v
    for v in item.values():
        if isinstance(v, str) and v.startswith("http"):
            return v
    return None


def probe(url):
    """Tamaño y cabeceras CORS del fichero, sin descargarlo entero."""
    info = {"size": None, "cors": None, "status": None}
    for method, extra in (("HEAD", {}), ("GET", {"Range": "bytes=0-0"})):
        try:
            req = urllib.request.Request(url, method=method, headers={"User-Agent": UA, "Origin": ORIGIN, **extra})
            with urllib.request.urlopen(req, timeout=20) as r:
                info["status"] = r.status
                h = r.headers
                info["cors"] = h.get("Access-Control-Allow-Origin")
                cr = h.get("Content-Range")
                if cr and "/" in cr and cr.rsplit("/", 1)[1].isdigit():
                    info["size"] = int(cr.rsplit("/", 1)[1])
                elif h.get("Content-Length") and method == "HEAD":
                    info["size"] = int(h["Content-Length"])
            if info["size"]:
                return info
        except (urllib.error.URLError, ValueError, TimeoutError) as e:
            info["error"] = str(e)[:200]
    return info


def main():
    raw = {}
    servers = {}
    regions = set()

    for length in ("short", "long"):
        try:
            payload = get_json(f"{API}?test_length={length}")
        except Exception as e:  # noqa: BLE001
            raw[f"nodefault_{length}"] = {"error": str(e)[:300]}
            continue
        raw[f"default_{length}"] = payload
        for it in items_of(payload):
            if isinstance(it, dict) and isinstance(it.get("region"), str):
                regions.add(it["region"])

    # Pedimos también cada región conocida, porque sin región TorBox elige
    # la más cercana a la IP de GitHub (en EE. UU.), no a España.
    for region in sorted(regions):
        for length in ("short", "long"):
            try:
                payload = get_json(f"{API}?test_length={length}&region={urllib.request.quote(region)}")
                raw[f"{region}_{length}"] = payload
            except Exception as e:  # noqa: BLE001
                raw[f"{region}_{length}"] = {"error": str(e)[:300]}

    for key, payload in raw.items():
        length = key.rsplit("_", 1)[-1]
        for it in items_of(payload):
            url = find_url(it)
            if not url or url in servers:
                continue
            entry = {k: v for k, v in it.items() if isinstance(v, (str, int, float, bool)) or v is None}
            entry["url"] = url
            entry["length"] = length
            entry.update(probe(url))
            servers[url] = entry

    out = {
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "servers": list(servers.values()),
    }
    with open("servers.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    with open("scripts/ultima_respuesta_api.json", "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=1)
    print(f"{len(servers)} servidores, regiones: {sorted(regions)}")


if __name__ == "__main__":
    main()
