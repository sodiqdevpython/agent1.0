import os, sys, time, json, uuid, threading, requests
from concurrent.futures import ThreadPoolExecutor

from pywintrace import ETW, ProviderInfo, GUID
from fast_sigma_runtime import analyze_log, ensure_sigma_cache
from notifypy import Notify


ensure_sigma_cache()


DEVICE_API  = "http://13.60.91.11:8000/api/v1/agent/device/list/"
device_id   = None          # global
def get_local_mac() -> str:
    raw = hex(uuid.getnode())[2:].zfill(12).upper()
    return ":".join(raw[i:i+2] for i in range(0, 12, 2))

def identify_device() -> int | None:
    try:
        r = requests.get(DEVICE_API, timeout=5)
        r.raise_for_status()
        mac = get_local_mac()
        for dev in r.json():
            if dev.get("mac_address", "").upper() == mac:
                print(f"[i] Qurilma topildi → id={dev['pk']} (MAC {mac})")
                return dev["pk"]
        print(f"[!] MAC {mac} bo‘yicha qurilma topilmadi.")
    except Exception as e:
        print("[!] Device API xatosi:", e)
    return None

device_id = identify_device()

ES_URL = "https://search-siemlog-rddlwektckldlou57enditbsqa.eu-north-1.es.amazonaws.com/abc/_doc"
MISMATCH_URL = "http://13.60.91.11:8000/api/v1/elastic/mismatches/"
ES_AUTH = ("sardor", "Aws0000$")
ES_HEADERS = {"Content-Type": "application/json"}


if getattr(sys, "frozen", False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))
icon_path  = os.path.join(base_path, "logo.png")
sound_path = os.path.join(base_path, "notification.wav")

def notify(title: str, text: str = ""):
    sys.stderr = open(os.devnull, "w")          # notifypy stderr’ni to‘sadi
    text = text[:60] + "..." if len(text) > 60 else text
    n = Notify()
    n.title = title
    n.message = text
    if os.path.exists(icon_path):
        n.icon = icon_path
    if os.path.exists(sound_path):
        n.audio = sound_path
    n.application_name = "Agent"
    n.send()

pool = ThreadPoolExecutor(max_workers=2)

def send_mismatch(es_id: str, sigma_rule_id: str):
    if not (device_id and es_id):
        return
    payload = {
        "device": device_id,
        "mismatch_log_id": es_id,
        "mismatch_sigma_rule_id": sigma_rule_id,
    }
    try:
        r = requests.post(MISMATCH_URL, json=payload, timeout=4)
        if r.status_code not in (200, 201):
            print("Mismatch API xato:", r.status_code, r.text[:120])
    except Exception as e:
        print("Mismatch API xatosi:", e)

def post_to_es(doc: dict) -> str | None:
    try:
        r = requests.post(ES_URL, json=doc, auth=ES_AUTH, headers=ES_HEADERS, timeout=4)
        if r.status_code in (200, 201):
            return r.json().get("_id")
        print("ES xato:", r.status_code, r.text[:120])
    except Exception as e:
        print("ES Connection xato:", e)
    return None

EXCLUDE_DIRS = [p.lower() for p in [
    r"c:\users\sodiq\appdata\local\programs\microsoft vs code\code.exe",
    r"C:\Users\sodiq\AppData\Local\Programs\Python\Python310\python.exe",
    r"C:\Users\sodiq\Desktop\log_agent_backend\env\Scripts\python.exe"
]]
AGENT_PATH = os.path.realpath(sys.executable).lower()

def callback(full_event):
    event_id, event = full_event
    doc = {"EventId": event_id, "Event": event}

    evhdr = event.get("EventHeader", {}).get("EventDescriptor", {})
    evhdr["Keyword"] = str(evhdr.get("Keyword", "0"))

    img  = event.get("Image", "X").lower()
    pimg = event.get("ParentImage", "X").lower()
    if img == AGENT_PATH or pimg == AGENT_PATH or img in EXCLUDE_DIRS or pimg in EXCLUDE_DIRS:
        return

    hits  = analyze_log(event)
    es_id = post_to_es(doc)

    if hits:
        h0 = hits[0]
        notify(h0["title"], h0["desc"])
        for h in hits:
            pool.submit(send_mismatch, es_id, h["id"])

provider = ProviderInfo("Microsoft-Windows-Sysmon", GUID("{5770385F-C22A-43E0-BF4C-06F5698FFBD9}"))
etw = ETW(providers=[provider], event_callback=callback)

try:
    etw.start()
except Exception as e:
    import traceback; traceback.print_exc(); sys.exit("ETW boshlanmadi (admin huquqi yoki Sysmon yo‘q)")

try:
    while True:
        time.sleep(2)
except KeyboardInterrupt:
    print("Agent to‘xtadi (CTRL+C)")
finally:
    etw.stop()
    pool.shutdown(wait=False)
