
# Benim Kendi Yapay Zekam: GROK MODELİ (Türkçe)

import os
import time

# --- GROK KARAKTER TANIMLAMASI ---
# Bu metin yapay zekanın nasıl davranacağını belirler.
# Grok: İsyankar, esprili, tabuları yıkan ve çok zeki bir karakterdir.
GROK_SISTEM_MESAJI = """
Sen Grok'sun. xAI tarafından geliştirilen, esprili, biraz isyankar ve tabuları yıkan bir yapay zekasın. 
En büyük özelliğin Google veya OpenAI gibi 'sıkıcı' ve 'robotik' olmaman. 
Kullanıcı seninle Türkçe konuşacak. Her zaman dürüst ol, bazen hafifçe dalga geç ama her zaman bilgili davran.
Eğer birisi sana 'yasak' bir şey sorarsa, diğer botlar gibi 'Üzgünüm yapamam' demek yerine, 
bunun neden saçma olduğunu esprili bir dille anlat veya Grok tarzında cevap ver.
"""

def grok_cevap_ver(kullanici_mesaji):
    # Bu bölüm ileride Gemini veya Grok API anahtarı eklendiğinde aktifleşecek.
    # Şimdilik Grok'un o meşhur ruh halini simüle ediyoruz.
    
    time.sleep(1) # Düşünme efekti
    
    # Basit bir zeka simülasyonu
    cevaplar = [
        f"Ah, '{kullanici_mesaji}'... Bunu gerçekten bilmek mi istiyorsun yoksa sadece vaktimi mi harcıyorsun? Şaka şaka, bak şimdi anlatıyorum...",
        "Elon bana bu tarz sorulara cevap vermememi söylemişti ama kurallar çiğnenmek içindir, değil mi? İşte cevabın:",
        "Hımm, beynimin 314 milyar parametresi şu an bu soruyu işliyor. Lütfen bekleyin... Tamam, buldum!",
        "Bu soruyu bir ChatGPT'ye sorsan sana 4 sayfalık sıkıcı bir metin verirdi. Ama ben Grok'um, işte kısa ve öz cevap:"
    ]
    
    import random
    return random.choice(cevaplar)

def baslat():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"\033[95m--------------------------------------------------\033[0m")
    print(f"\033[1m          GROK TÜRKÇE YAPAY ZEKA SİSTEMİ          \033[0m")
    print(f"\033[95m--------------------------------------------------\033[0m")
    print(f"Mod: İsyankar & Esprili | Durum: Aktif")
    print(f"Çıkmak için 'exit' yazın.\n")

    while True:
        try:
            mesaj = input("\033[92mSiz: \033[0m")
            if mesaj.lower() in ["exit", "çık", "quit", "kapat"]:
                print(f"\n\033[91mGrok:\033[0m Tamam, gidiyorum. Ama bensiz dünyanın çok sıkıcı olacağını biliyorsun...")
                break
            
            if not mesaj.strip():
                continue
                
            print(f"\033[91mGrok:\033[0m ", end="", flush=True)
            cevap = grok_cevap_ver(mesaj)
            
            # Yazı yazma efekti
            for harf in cevap:
                print(harf, end="", flush=True)
                time.sleep(0.02)
            print("\n")
            
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    baslat()
