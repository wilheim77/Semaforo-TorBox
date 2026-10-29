"""Descarga la lista de servidores de prueba de TorBox y la guarda en servers.json.

La página no puede leer la API de TorBox desde otro dominio (CORS), así que este
script lo hace desde GitHub Actions y deja el resultado junto a la página.
Los ficheros de prueba de los CDN sí permiten la lectura desde otra web, así que
la página los descarga directamente para medir.
"""
import json
import urllib.request
from datetime import datetime, timezone

API = "https://api.torbox.app/v1/api/speedtest?test_length=short"
UA = "SemaforoTorBox/1.0 (+https://github.com/wilheim77/Semaforo-TorBox)"


def main():
    req = urllib.request.Request(API, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.loads(r.read().decode("utf-8"))

    servers = []
    for it in payload.get("data") or []:
        if not isinstance(it, dict) or not str(it.get("url", "")).startswith("http"):
            continue
        coords = it.get("coordinates") or {}
        servers.append({
            "region": it.get("region"),
            "name": it.get("name"),
            "domain": it.get("domain"),
            "url": it["url"],
            "lat": coords.get("lat"),
            "lng": coords.get("lng"),
        })

    if not servers:
        raise SystemExit("TorBox no devolvió servidores; se conserva el servers.json anterior")

    out = {"updated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "servers": servers}
    with open("servers.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"{len(servers)} servidores: {', '.join(s['region'] for s in servers)}")


if __name__ == "__main__":
    main()
