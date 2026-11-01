# Tebex Plugin API'den son 30 günün tamamlanmış, ücretli ödemelerini okur; en çok satan 3 paketin
# yalnız id'sini best.json'a yazar. Satış sayısı dosyaya girmez (mağazada gösterilmez).
# Son ücretli siparişlerin paket adlarını ve maskeli oyuncu adını recent.json'a yazar (Recent Payments modülü tek ad verir).
# Repo public: tam oyuncu adı dosyaya ve git geçmişine girmez.
import json, os, sys, urllib.error, urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone

TABAN = os.environ.get("TEBEX_API", "https://plugin.tebex.io")
ANAHTAR = os.environ.get("TEBEX_SECRET", "")
GUN = 30
ADET = 3
SON_SIPARIS = 12


def sayfa(n):
    istek = urllib.request.Request(f"{TABAN}/payments?paged=1&page={n}",
                                   headers={"X-Tebex-Secret": ANAHTAR, "User-Agent": "muto-best-sellers"})
    try:
        with urllib.request.urlopen(istek, timeout=30) as y:
            return json.load(y)
    except urllib.error.HTTPError as h:
        sys.exit(f"Tebex {h.code}: {h.read()[:200].decode('utf-8', 'replace')}")


def maske(ad):
    # sabit uzunluk: ad uzunluğu da sızmaz
    return ad[:1] + "***" if ad else ""


def tarih(s):
    # Tebex '2016-01-27T15:40:19+0000' verir; fromisoformat '+0000'ı 3.11'den önce okumaz
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S%z")


def main():
    if not ANAHTAR:
        sys.exit("TEBEX_SECRET yok")
    sinir = datetime.now(timezone.utc) - timedelta(days=GUN)
    sayac, son, siparisler = Counter(), {}, []
    n = 1
    while True:
        j = sayfa(n)
        veri = j.get("data", [])
        eski = 0
        for p in veri:
            t = tarih(p["date"])
            if t < sinir:
                eski += 1
                continue
            if str(p.get("status", "")).lower() != "complete" or float(p.get("amount") or 0) <= 0:
                continue
            if len(siparisler) < SON_SIPARIS:
                siparisler.append({"n": maske((p.get("player") or {}).get("name")),
                                   "p": [pk["name"] for pk in p.get("packages", [])]})
            for pk in p.get("packages", []):
                sayac[pk["id"]] += 1
                son[pk["id"]] = max(son.get(pk["id"], t), t)
        # sayfalar yeniden eskiye; tamamı sınır dışındaysa devam etmeye gerek yok
        if not veri or eski == len(veri) or n >= int(j.get("last_page") or n):
            break
        n += 1
    # eşitlikte son satışı daha yeni olan önde
    sira = sorted(sayac, key=lambda k: (-sayac[k], -son[k].timestamp()))[:ADET]
    with open("best.json", "w", encoding="utf-8") as f:
        json.dump({"ids": sira}, f)
        f.write("\n")
    with open("recent.json", "w", encoding="utf-8") as f:
        json.dump({"items": siparisler}, f, ensure_ascii=False)
        f.write("\n")
    print("ids:", sira, "siparis:", len(siparisler))


if __name__ == "__main__":
    main()
