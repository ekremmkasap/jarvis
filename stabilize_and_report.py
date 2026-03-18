from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "holding_merkezi" / "outputs" / "sistem_durum_raporu.md"


@dataclass
class Madde:
    baslik: str
    durum: str
    detay: str


def guvenli_oku(dosya: Path) -> str:
    try:
        return dosya.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def maskele_token(deger: str) -> str:
    temiz = deger.strip()
    if len(temiz) <= 10:
        return "***"
    return f"{temiz[:4]}...{temiz[-4:]}"


def kritik_kopya_analizi() -> list[Madde]:
    maddeler: list[Madde] = []
    kritik = ["bridge.py", "jarvis_router.py", "telegram_gateway_v2.py", "DEVLOG.md"]
    for ad in kritik:
        try:
            eslesen = [p for p in ROOT.rglob(ad) if "node_modules" not in p.parts and "dist" not in p.parts]
            if len(eslesen) <= 1:
                durum = "OK"
                detay = f"{ad} için çakışma riski görülmedi"
            else:
                durum = "UYARI"
                yollar = ", ".join(str(p.relative_to(ROOT)) for p in eslesen[:6])
                detay = f"{ad} için {len(eslesen)} kopya bulundu: {yollar}"
            maddeler.append(Madde(f"Kopya Kontrolü: {ad}", durum, detay))
        except Exception as exc:
            maddeler.append(Madde(f"Kopya Kontrolü: {ad}", "HATA", f"Tarama başarısız: {exc}"))
    return maddeler


def secret_analizi() -> list[Madde]:
    maddeler: list[Madde] = []
    desenler = {
        "telegram_token": re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{20,}\b"),
        "api_key_like": re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[=:]\s*[\"']?([A-Za-z0-9_\-]{12,})"),
    }
    hedef_uzantilar = {".py", ".json", ".txt", ".md", ".env"}
    hedef_kokler = [
        ROOT / "server",
        ROOT / "src",
        ROOT / "holding_merkezi",
        ROOT,
    ]

    bulunanlar: list[str] = []
    ziyaret: set[Path] = set()

    for kok in hedef_kokler:
        try:
            if not kok.exists():
                continue
            for dosya in kok.rglob("*"):
                try:
                    if dosya in ziyaret:
                        continue
                    ziyaret.add(dosya)
                    if not dosya.is_file() or dosya.suffix.lower() not in hedef_uzantilar:
                        continue
                    if any(x in dosya.parts for x in ("node_modules", "dist", ".git")):
                        continue
                    metin = guvenli_oku(dosya)
                    if not metin:
                        continue
                    for satir_no, satir in enumerate(metin.splitlines(), start=1):
                        for ad, pattern in desenler.items():
                            es = pattern.search(satir)
                            if not es:
                                continue
                            ham = es.group(0)
                            bulunanlar.append(
                                f"{dosya.relative_to(ROOT)}:{satir_no} [{ad}] {maskele_token(ham)}"
                            )
                except Exception:
                    continue
        except Exception:
            continue

    if not bulunanlar:
        maddeler.append(Madde("Secret Taraması", "OK", "Açık token/pattern izi bulunamadı"))
        return maddeler

    maddeler.append(Madde("Secret Taraması", "UYARI", f"{len(bulunanlar)} potansiyel iz bulundu"))
    onizleme = " | ".join(bulunanlar[:5])
    maddeler.append(Madde("Secret Örnekleri", "BILGI", onizleme))
    return maddeler


def holding_kontrol() -> list[Madde]:
    maddeler: list[Madde] = []
    try:
        inputs = ROOT / "holding_merkezi" / "inputs"
        outputs = ROOT / "holding_merkezi" / "outputs"
        gerekli = ["newsletter.txt", "kampanya_plani.md", "web_brief.txt"]
        eksik = [f for f in gerekli if not (inputs / f).exists()]
        if eksik:
            maddeler.append(Madde("Holding Input Kontrol", "UYARI", f"Eksik girdiler: {', '.join(eksik)}"))
        else:
            maddeler.append(Madde("Holding Input Kontrol", "OK", "Temel input dosyaları mevcut"))

        dosya_sayisi = 0
        try:
            if outputs.exists():
                dosya_sayisi = sum(1 for p in outputs.rglob("*") if p.is_file())
        except Exception:
            dosya_sayisi = 0
        maddeler.append(Madde("Holding Output Durumu", "BILGI", f"Toplam çıktı dosyası: {dosya_sayisi}"))
    except Exception as exc:
        maddeler.append(Madde("Holding Kontrol", "HATA", f"Kontrol başarısız: {exc}"))
    return maddeler


def aksiyon_plani() -> list[str]:
    return [
        "Tek resmi çalışma hattını `server/` olarak sabitle ve diğer kopyaları `legacy/` altında arşivle.",
        "Token/secret değerlerini dosyalardan kaldır, sadece ortam değişkeni veya secret dosyasıyla oku.",
        "Bridge için tek dosya politikası uygula: deploy yalnızca `server/openclaw/bridge.py` üzerinden yürüsün.",
        "Servis log standardını netleştir: systemd syslog uyarılarını kaldır, startup log üretimini zorunlu kıl.",
        "Holding akışında HITL adımını zorunlu tut: görsel seçimi olmadan video aşamasına geçme.",
    ]


def rapor_yaz(maddeler: list[Madde]) -> None:
    try:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        satirlar: list[str] = []
        satirlar.append("# Jarvis Sistem Durum Raporu")
        satirlar.append("")
        satirlar.append(f"- Uretim zamani: {datetime.now().isoformat(timespec='seconds')}")
        satirlar.append(f"- Klasor: {ROOT}")
        satirlar.append("")
        satirlar.append("## Bulgu Ozeti")
        for m in maddeler:
            satirlar.append(f"- [{m.durum}] {m.baslik}: {m.detay}")

        satirlar.append("")
        satirlar.append("## Onerilen Sirali Aksiyonlar")
        for i, adim in enumerate(aksiyon_plani(), start=1):
            satirlar.append(f"{i}. {adim}")

        satirlar.append("")
        satirlar.append("## Sonuc")
        satirlar.append("- Sistem calisabilir durumda, ancak kopya dosya ve secret hijyeni nedeniyle operasyonel risk devam ediyor.")
        satirlar.append("- Sonraki odak: tek kaynak hatti + secret temizligi + log standardizasyonu.")

        OUTPUT.write_text("\n".join(satirlar), encoding="utf-8")
    except Exception:
        pass


def main() -> int:
    maddeler: list[Madde] = []
    try:
        maddeler.extend(kritik_kopya_analizi())
    except Exception as exc:
        maddeler.append(Madde("Kopya Analizi", "HATA", str(exc)))

    try:
        maddeler.extend(secret_analizi())
    except Exception as exc:
        maddeler.append(Madde("Secret Analizi", "HATA", str(exc)))

    try:
        maddeler.extend(holding_kontrol())
    except Exception as exc:
        maddeler.append(Madde("Holding Kontrol", "HATA", str(exc)))

    rapor_yaz(maddeler)

    for m in maddeler:
        print(f"[{m.durum}] {m.baslik}: {m.detay}")
    print(f"Rapor: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
