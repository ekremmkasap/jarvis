import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import time
import threading
import asyncio
import edge_tts
import pygame
import speech_recognition as sr
import subprocess
import os
import webbrowser
import datetime
import math
import tempfile
import sys
import winreg

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

pygame.mixer.init()

hand_was_detected = False

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7,
)

SCREEN_W, SCREEN_H = pyautogui.size()

SMOOTHING = 5
prev_x, prev_y = 0, 0

CLICK_COOLDOWN = 0.5
last_click_time = 0

ALT_TAB_COOLDOWN = 1.0
last_alt_tab_time = 0

scroll_anchor_y = None
SCROLL_DEAD_ZONE = 0.03
SCROLL_SPEED = 150

VOICE = "tr-TR-AhmetNeural"

recognizer = sr.Recognizer()
microphone = sr.Microphone()

jarvis_listening = False
jarvis_status = "HAZIR"
jarvis_last_text = ""
jarvis_log = []
MAX_LOG = 5
frame_count = 0

tts_lock = threading.Lock()


def jarvis_speak(text):
    global jarvis_status, jarvis_last_text
    jarvis_last_text = text
    jarvis_log.append(("JARVIS", text))
    if len(jarvis_log) > MAX_LOG:
        jarvis_log.pop(0)
    jarvis_status = "KONUSUYOR"
    print(f"[JARVIS] {text}")
    with tts_lock:
        try:
            tmp = os.path.join(tempfile.gettempdir(), "jarvis_tts.mp3")
            asyncio.run(_tts_generate(text, tmp))
            pygame.mixer.music.load(tmp)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.05)
            pygame.mixer.music.unload()
        except Exception as e:
            print(f"TTS hata: {e}")
    jarvis_status = "HAZIR"


async def _tts_generate(text, path):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(path)


def process_command(command):
    cmd = command.lower().strip()

    if any(w in cmd for w in ["merhaba", "selam", "hey"]):
        jarvis_speak("Merhaba efendim. Size nasıl yardımcı olabilirim?")
        return
    if any(w in cmd for w in ["saat kaç", "saat kac", "saati söyle"]):
        now = datetime.datetime.now().strftime("%H:%M")
        jarvis_speak(f"Saat şu an {now} efendim.")
        return
    if any(w in cmd for w in ["tarih", "bugün günlerden", "gün ne", "gun ne"]):
        today = datetime.datetime.now().strftime("%d %B %Y %A")
        jarvis_speak(f"Bugün {today} efendim.")
        return
    if any(w in cmd for w in ["google", "ara", "arama yap"]):
        query = cmd
        for w in ["google", "jarvis", "ara", "arama yap", "'da", "de", "da"]:
            query = query.replace(w, "")
        query = query.strip()
        if query:
            webbrowser.open(f"https://www.google.com/search?q={query}")
            jarvis_speak(f"{query} için arama yapıyorum efendim.")
        else:
            jarvis_speak("Ne aramamı istersiniz efendim?")
        return
    if any(w in cmd for w in ["youtube", "video"]):
        query = cmd
        for w in ["youtube", "jarvis", "video", "aç", "ac", "'ta", "ta", "da", "de"]:
            query = query.replace(w, "")
        query = query.strip()
        if query:
            webbrowser.open(f"https://www.youtube.com/results?search_query={query}")
            jarvis_speak(f"YouTube'da {query} arıyorum efendim.")
        else:
            webbrowser.open("https://www.youtube.com")
            jarvis_speak("YouTube'u açıyorum efendim.")
        return
    if any(w in cmd for w in ["not defteri", "notepad"]):
        subprocess.Popen("notepad.exe")
        jarvis_speak("Not defterini açıyorum efendim.")
        return
    if any(w in cmd for w in ["hesap makinesi", "calculator"]):
        subprocess.Popen("calc.exe")
        jarvis_speak("Hesap makinesini açıyorum efendim.")
        return
    if any(w in cmd for w in ["dosya gezgini", "explorer", "dosyalar"]):
        subprocess.Popen("explorer.exe")
        jarvis_speak("Dosya gezginini açıyorum efendim.")
        return
    if any(w in cmd for w in ["müzik", "muzik", "spotify"]):
        try:
            os.startfile("spotify:")
            jarvis_speak("Spotify açılıyor efendim.")
        except Exception:
            jarvis_speak("Spotify bulunamadı efendim.")
        return
    if any(w in cmd for w in ["kapat", "sistemi kapat", "bilgisayarı kapat"]):
        jarvis_speak("Sistemi kapatmak üzere. İyi geceler efendim.")
        os.system("shutdown /s /t 10")
        return
    if any(w in cmd for w in ["iptal", "kapatma iptal"]):
        os.system("shutdown /a")
        jarvis_speak("Kapatma işlemi iptal edildi efendim.")
        return
    if any(w in cmd for w in ["nasılsın", "nasilsin", "iyi misin"]):
        jarvis_speak("Ben bir yapay zekayım efendim ama sizin için her zaman hazırım.")
        return
    if any(w in cmd for w in ["sen kimsin", "kimsin", "adın ne", "adin ne"]):
        jarvis_speak("Ben JARVIS. Just A Rather Very Intelligent System. Sizin kişisel yapay zeka asistanınızım efendim.")
        return
    if any(w in cmd for w in ["teşekkür", "sağ ol", "sag ol"]):
        jarvis_speak("Rica ederim efendim. Her zaman hizmetinizdeyim.")
        return
    if any(w in cmd for w in ["görüşürüz", "hoşça kal", "bye"]):
        jarvis_speak("Görüşürüz efendim. İyi günler dilerim.")
        return
    if any(w in cmd for w in ["ekranı kilitle", "kilitle", "lock"]):
        os.system("rundll32.exe user32.dll,LockWorkStation")
        jarvis_speak("Ekran kilitleniyor efendim.")
        return
    if any(w in cmd for w in ["ses aç", "sesi aç", "ses ac"]):
        pyautogui.press("volumeup", presses=5)
        jarvis_speak("Ses seviyesini artırıyorum efendim.")
        return
    if any(w in cmd for w in ["ses kıs", "sesi kıs", "ses kis"]):
        pyautogui.press("volumedown", presses=5)
        jarvis_speak("Ses seviyesini düşürüyorum efendim.")
        return
    if any(w in cmd for w in ["sessize al", "sessiz", "mute"]):
        pyautogui.press("volumemute")
        jarvis_speak("Ses kapatıldı efendim.")
        return

    jarvis_speak(f"Üzgünüm efendim, '{command}' komutunu anlayamadım. Başka bir şey deneyin.")


def listen_loop():
    global jarvis_listening, jarvis_status
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)

    while True:
        if not jarvis_listening:
            time.sleep(0.1)
            continue

        jarvis_status = "DİNLİYOR"
        try:
            with microphone as source:
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=8)
            jarvis_status = "İŞLİYOR"
            text = recognizer.recognize_google(audio, language="tr-TR")
            jarvis_log.append(("SİZ", text))
            if len(jarvis_log) > MAX_LOG:
                jarvis_log.pop(0)
            print(f"[SİZ] {text}")
            process_command(text)
        except sr.WaitTimeoutError:
            jarvis_status = "HAZIR"
        except sr.UnknownValueError:
            jarvis_speak("Anlayamadım efendim, tekrar söyler misiniz?")
        except sr.RequestError:
            jarvis_speak("İnternet bağlantısı sorunu var efendim.")
            jarvis_status = "HAZIR"
        except Exception:
            jarvis_status = "HAZIR"

        jarvis_listening = False


C_CYAN = (255, 200, 0)
C_ORANGE = (0, 140, 255)
C_BLUE = (255, 150, 0)
C_RED = (0, 0, 255)
C_GREEN = (0, 255, 100)
C_WHITE = (220, 220, 220)
C_DARK = (15, 15, 15)
C_GOLD = (0, 215, 255)


def draw_arc(img, center, radius, start_deg, end_deg, color, thickness=2):
    cv2.ellipse(img, center, (radius, radius), 0, start_deg, end_deg, color, thickness, cv2.LINE_AA)


def draw_hud(frame, gesture_text):
    h, w, _ = frame.shape
    t = time.time()
    overlay = frame.copy()

    cv2.rectangle(overlay, (0, 0), (w, 55), C_DARK, -1)
    cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)

    cv2.line(frame, (0, 55), (w, 55), C_CYAN, 1, cv2.LINE_AA)

    overlay2 = frame.copy()
    log_area_h = 30 * min(len(jarvis_log) + 1, MAX_LOG + 1) + 15
    cv2.rectangle(overlay2, (0, h - log_area_h), (w, h), C_DARK, -1)
    cv2.addWeighted(overlay2, 0.75, frame, 0.25, 0, frame)
    cv2.line(frame, (0, h - log_area_h), (w, h - log_area_h), C_CYAN, 1, cv2.LINE_AA)

    cv2.putText(frame, "J.A.R.V.I.S", (15, 38),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, C_GOLD, 2, cv2.LINE_AA)

    pulse = int(abs(math.sin(t * 3)) * 80) + 175
    cv2.putText(frame, "//", (210, 38),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (pulse, pulse // 2, 0), 2, cv2.LINE_AA)

    now_str = datetime.datetime.now().strftime("%H:%M:%S")
    cv2.putText(frame, now_str, (240, 38),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, C_WHITE, 1, cv2.LINE_AA)

    status_colors = {
        "HAZIR": C_GREEN,
        "DİNLİYOR": (0, 255, 255),
        "KONUSUYOR": C_ORANGE,
        "İŞLİYOR": C_GOLD,
    }
    s_color = status_colors.get(jarvis_status, C_CYAN)

    status_x = w - 200
    cv2.circle(frame, (status_x - 15, 33), 6, s_color, -1, cv2.LINE_AA)
    blink = int(abs(math.sin(t * 4)) * 8) + 8
    cv2.circle(frame, (status_x - 15, 33), blink, s_color, 1, cv2.LINE_AA)
    cv2.putText(frame, jarvis_status, (status_x, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, s_color, 2, cv2.LINE_AA)

    cx_r, cy_r = w - 45, 30
    r1 = 18
    a1 = int(t * 120) % 360
    draw_arc(frame, (cx_r, cy_r), r1, a1, a1 + 90, C_CYAN, 2)
    draw_arc(frame, (cx_r, cy_r), r1, a1 + 180, a1 + 270, C_ORANGE, 2)
    r2 = 12
    a2 = -int(t * 180) % 360
    draw_arc(frame, (cx_r, cy_r), r2, a2, a2 + 60, C_GOLD, 1)

    corners = [
        ((10, 60), (40, 60), (10, 60), (10, 90)),
        ((w - 40, 60), (w - 10, 60), (w - 10, 60), (w - 10, 90)),
        ((10, h - log_area_h - 30), (40, h - log_area_h - 30), (10, h - log_area_h - 30), (10, h - log_area_h)),
        ((w - 40, h - log_area_h - 30), (w - 10, h - log_area_h - 30), (w - 10, h - log_area_h - 30), (w - 10, h - log_area_h)),
    ]
    for (x1, y1), (x2, y2), (x3, y3), (x4, y4) in corners:
        cv2.line(frame, (x1, y1), (x2, y2), C_CYAN, 1, cv2.LINE_AA)
        cv2.line(frame, (x3, y3), (x4, y4), C_CYAN, 1, cv2.LINE_AA)

    overlay3 = frame.copy()
    cv2.rectangle(overlay3, (15, h - log_area_h + 5), (w - 15, h - 5), (30, 30, 30), -1)
    cv2.addWeighted(overlay3, 0.5, frame, 0.5, 0, frame)

    cv2.putText(frame, "KOMUT GECMISI", (20, h - log_area_h + 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, C_GOLD, 1, cv2.LINE_AA)

    for i, (speaker, text) in enumerate(jarvis_log[-MAX_LOG:]):
        y_pos = h - log_area_h + 42 + i * 28
        if speaker == "JARVIS":
            cv2.putText(frame, f"> {text[:70]}", (25, y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, C_GOLD, 1, cv2.LINE_AA)
        else:
            cv2.putText(frame, f"  {text[:70]}", (25, y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, C_WHITE, 1, cv2.LINE_AA)

    gesture_label = {
        "MOVE": "FARE KONTROL",
        "CLICK": "SOL TIK",
        "FIST": "SAG TIK",
        "OPEN_HAND": "SCROLL",
        "ALT_TAB": "PENCERE GECIS",
        "UNKNOWN": "---",
        "---": "---",
    }
    g_text = gesture_label.get(gesture_text, gesture_text)

    box_w = 200
    box_x = w - box_w - 15
    box_y = 70

    overlay4 = frame.copy()
    cv2.rectangle(overlay4, (box_x, box_y), (box_x + box_w, box_y + 60), C_DARK, -1)
    cv2.addWeighted(overlay4, 0.7, frame, 0.3, 0, frame)
    cv2.rectangle(frame, (box_x, box_y), (box_x + box_w, box_y + 60), C_CYAN, 1, cv2.LINE_AA)

    cv2.putText(frame, "HAREKET", (box_x + 10, box_y + 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, C_CYAN, 1, cv2.LINE_AA)

    g_color = C_GREEN if g_text not in ["---"] else C_WHITE
    cv2.putText(frame, g_text, (box_x + 10, box_y + 48),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, g_color, 2, cv2.LINE_AA)

    info_x = 15
    info_y = 70
    overlay5 = frame.copy()
    cv2.rectangle(overlay5, (info_x, info_y), (info_x + 200, info_y + 90), C_DARK, -1)
    cv2.addWeighted(overlay5, 0.7, frame, 0.3, 0, frame)
    cv2.rectangle(frame, (info_x, info_y), (info_x + 200, info_y + 90), C_CYAN, 1, cv2.LINE_AA)

    cv2.putText(frame, "KONTROLLER", (info_x + 8, info_y + 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, C_CYAN, 1, cv2.LINE_AA)
    controls = ["V : Sesli Komut", "Q : Cikis"]
    for i, ctrl in enumerate(controls):
        cv2.putText(frame, ctrl, (info_x + 8, info_y + 40 + i * 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, C_WHITE, 1, cv2.LINE_AA)

    scan_y = 60 + int((t * 50) % (h - log_area_h - 60))
    alpha_line = 0.3
    line_overlay = frame.copy()
    cv2.line(line_overlay, (0, scan_y), (w, scan_y), C_CYAN, 1, cv2.LINE_AA)
    cv2.addWeighted(line_overlay, alpha_line, frame, 1 - alpha_line, 0, frame)

    return frame


def count_fingers(hand_landmarks):
    tips = [
        mp_hands.HandLandmark.INDEX_FINGER_TIP,
        mp_hands.HandLandmark.MIDDLE_FINGER_TIP,
        mp_hands.HandLandmark.RING_FINGER_TIP,
        mp_hands.HandLandmark.PINKY_TIP,
    ]
    pips = [
        mp_hands.HandLandmark.INDEX_FINGER_PIP,
        mp_hands.HandLandmark.MIDDLE_FINGER_PIP,
        mp_hands.HandLandmark.RING_FINGER_PIP,
        mp_hands.HandLandmark.PINKY_PIP,
    ]

    fingers_up = []
    for tip, pip_ in zip(tips, pips):
        if hand_landmarks.landmark[tip].y < hand_landmarks.landmark[pip_].y:
            fingers_up.append(True)
        else:
            fingers_up.append(False)

    thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
    thumb_ip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_IP]
    thumb_up = thumb_tip.x < thumb_ip.x

    return thumb_up, fingers_up


def get_gesture(thumb_up, fingers_up):
    total = sum(fingers_up) + (1 if thumb_up else 0)

    if fingers_up[0] and not any(fingers_up[1:]) and not thumb_up:
        return "MOVE"
    if fingers_up[0] and fingers_up[1] and not fingers_up[2] and not fingers_up[3] and not thumb_up:
        return "CLICK"
    if total == 0:
        return "FIST"
    if total == 5:
        return "OPEN_HAND"
    if thumb_up and fingers_up[0] and not fingers_up[1] and not fingers_up[2] and not fingers_up[3]:
        return "ALT_TAB"

    return "UNKNOWN"


def draw_hand_effects(frame, hand_lm, gesture):
    h, w, _ = frame.shape
    t = time.time()

    mp_draw.draw_landmarks(frame, hand_lm, mp_hands.HAND_CONNECTIONS,
        mp_draw.DrawingSpec(color=C_CYAN, thickness=2, circle_radius=1),
        mp_draw.DrawingSpec(color=C_ORANGE, thickness=1))

    for lm in hand_lm.landmark:
        cx, cy = int(lm.x * w), int(lm.y * h)
        cv2.circle(frame, (cx, cy), 3, C_GOLD, -1, cv2.LINE_AA)

    index_tip = hand_lm.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    ix, iy = int(index_tip.x * w), int(index_tip.y * h)

    if gesture == "MOVE":
        cv2.circle(frame, (ix, iy), 12, C_GREEN, -1, cv2.LINE_AA)
        pulse = int(abs(math.sin(t * 5)) * 15) + 18
        cv2.circle(frame, (ix, iy), pulse, C_GREEN, 2, cv2.LINE_AA)
        cv2.circle(frame, (ix, iy), pulse + 8, C_GREEN, 1, cv2.LINE_AA)
        cv2.line(frame, (ix - 20, iy), (ix + 20, iy), C_GREEN, 1, cv2.LINE_AA)
        cv2.line(frame, (ix, iy - 20), (ix, iy + 20), C_GREEN, 1, cv2.LINE_AA)

    elif gesture == "CLICK":
        cv2.circle(frame, (ix, iy), 18, C_RED, 3, cv2.LINE_AA)
        cv2.circle(frame, (ix, iy), 8, C_RED, -1, cv2.LINE_AA)

    elif gesture == "OPEN_HAND":
        wrist = hand_lm.landmark[mp_hands.HandLandmark.WRIST]
        wx, wy = int(wrist.x * w), int(wrist.y * h)
        a = int(t * 100) % 360
        draw_arc(frame, (wx, wy), 30, a, a + 120, C_BLUE, 2)
        draw_arc(frame, (wx, wy), 30, a + 180, a + 300, C_ORANGE, 2)
        cv2.putText(frame, "SCROLL", (wx - 25, wy - 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, C_BLUE, 1, cv2.LINE_AA)

    elif gesture == "ALT_TAB":
        cv2.circle(frame, (ix, iy), 22, C_GOLD, 2, cv2.LINE_AA)
        a = int(t * 200) % 360
        for offset in [0, 90, 180, 270]:
            draw_arc(frame, (ix, iy), 30, a + offset, a + offset + 45, C_GOLD, 2)

    return frame


def add_to_startup():
    script_path = os.path.abspath(sys.argv[0])
    python_path = sys.executable
    cmd = f'"{python_path}" "{script_path}"'
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, "JARVIS_HandControl", 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)
        print("[JARVIS] Başlangıca eklendi.")
    except Exception as e:
        print(f"[JARVIS] Başlangıca eklenemedi: {e}")

def remove_from_startup():
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, "JARVIS_HandControl")
        winreg.CloseKey(key)
        print("[JARVIS] Başlangıçtan kaldırıldı.")
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"[JARVIS] Başlangıçtan kaldırılamadı: {e}")


def main():
    global prev_x, prev_y, last_click_time, last_alt_tab_time, scroll_anchor_y
    global jarvis_listening, frame_count, hand_was_detected

    add_to_startup()

    listen_thread = threading.Thread(target=listen_loop, daemon=True)
    listen_thread.start()

    cap = None
    for cam_index in [0, 1, 2]:
        print(f"Kamera {cam_index} deneniyor...")
        cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print(f"Kamera {cam_index} bulundu!")
                break
            cap.release()
        cap = None

    if cap is None:
        print("HATA: Kamera bulunamadi!")
        jarvis_speak("Efendim, kamera bulunamadı. Lütfen kamerayı kontrol edin.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    jarvis_speak("JARVIS sistemi aktif. Hizmetinizdeyim efendim. V tuşuna basarak benimle konuşabilirsiniz.")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.01)
            continue

        frame_count += 1
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)

        gesture_text = "---"

        if results.multi_hand_landmarks:
            for hand_lm in results.multi_hand_landmarks:
                thumb_up, fingers_up = count_fingers(hand_lm)
                gesture = get_gesture(thumb_up, fingers_up)
                gesture_text = gesture

                frame = draw_hand_effects(frame, hand_lm, gesture)

                index_tip = hand_lm.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                h, w, _ = frame.shape

                if gesture == "MOVE":
                    raw_x = index_tip.x
                    raw_y = index_tip.y
                    margin = 0.1
                    raw_x = np.clip((raw_x - margin) / (1 - 2 * margin), 0, 1)
                    raw_y = np.clip((raw_y - margin) / (1 - 2 * margin), 0, 1)
                    target_x = int(raw_x * SCREEN_W)
                    target_y = int(raw_y * SCREEN_H)
                    prev_x = prev_x + (target_x - prev_x) / SMOOTHING
                    prev_y = prev_y + (target_y - prev_y) / SMOOTHING
                    pyautogui.moveTo(int(prev_x), int(prev_y))

                elif gesture == "CLICK":
                    now = time.time()
                    if now - last_click_time > CLICK_COOLDOWN:
                        pyautogui.click()
                        last_click_time = now

                elif gesture == "FIST":
                    now = time.time()
                    if now - last_click_time > CLICK_COOLDOWN:
                        pyautogui.rightClick()
                        last_click_time = now

                elif gesture == "OPEN_HAND":
                    wrist_y = hand_lm.landmark[mp_hands.HandLandmark.WRIST].y
                    if scroll_anchor_y is None:
                        scroll_anchor_y = wrist_y
                    else:
                        delta = scroll_anchor_y - wrist_y
                        if abs(delta) > SCROLL_DEAD_ZONE:
                            scroll_amount = int(delta * SCROLL_SPEED)
                            pyautogui.scroll(scroll_amount)

                elif gesture == "ALT_TAB":
                    now = time.time()
                    if now - last_alt_tab_time > ALT_TAB_COOLDOWN:
                        pyautogui.hotkey("alt", "tab")
                        last_alt_tab_time = now

                if gesture != "OPEN_HAND":
                    scroll_anchor_y = None

        frame = draw_hud(frame, gesture_text)

        cv2.imshow("J.A.R.V.I.S", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            jarvis_speak("Sistem kapatılıyor. Görüşürüz efendim.")
            break
        elif key == ord("v") and not jarvis_listening:
            jarvis_listening = True

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
