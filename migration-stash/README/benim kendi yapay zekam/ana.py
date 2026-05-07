
# Yapay Zeka Backend (Arka Plan) Taslağı

import os

def yapay_zeka_cevap_ver(mesaj):
    # Bu fonksiyon ileride gerçek bir AI modeline (Gemini/GPT) bağlanacak
    cevap = f"Anladım, '{mesaj}' dedin. Ben senin Türkçe bilen yapay zekanım!"
    return cevap

if __name__ == "__main__":
    print("Yapay Zeka sistemi başlatılıyor...")
    while True:
        kullanici_girdisi = input("Siz: ")
        if kullanici_girdisi.lower() in ["çık", "kapat", "exit"]:
            print("Görüşürüz!")
            break
        
        cevap = yapay_zeka_cevap_ver(kullanici_girdisi)
        print(f"Zeka: {cevap}")
