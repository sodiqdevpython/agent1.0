import time, json, sys, os, requests, ctypes
from pywintrace import ETW, ProviderInfo, GUID
from fast_sigma_runtime import analyze_log
from win10toast_click import ToastNotifier
import webbrowser

POST_URL = "https://search-siemlog-rddlwektckldlou57enditbsqa.eu-north-1.es.amazonaws.com/abc/_doc"
AUTH = ("sardor", "Aws0000$")
HEADERS = {"Content-Type": "application/json"}


AGENT_PATH = os.path.realpath(sys.executable).lower()
toaster = ToastNotifier()


EXCLUDE_DIRS = [
    r'c:\users\sodiq\appdata\local\programs\microsoft vs code\code.exe',
    r'C:\Users\sodiq\AppData\Local\Programs\Microsoft VS Code\\',
    r'C:\\Users\\sodiq\\AppData\\Local\\Programs\\Python\\Python310\\python.exe',
    r'C:\Users\sodiq\AppData\Local\Programs\Python\Python310\python.exe'
]

EXCLUDE_DIRS = [path.lower() for path in EXCLUDE_DIRS]

def post(doc: dict):
    try:
        response = requests.post(POST_URL, json=doc, auth=AUTH, headers=HEADERS)
        if response.status_code not in [200, 201]:
            print("Qurilma internetga ulangan lekin wifi da internet yo'q yoki backendan muammo bor")
            print(response.text)
            with open('data.jsonl', 'a', encoding='utf-8') as file:
                file.write(json.dumps(doc, indent=4, ensure_ascii=False) + "\n")
    except Exception as exc:
        print("POST ishlamadi:", exc)


def open_url():
    webbrowser.open("https://google.com")
    return 0

def post_notification(title="Muammo aniqlandi", text=""):
    sys.stderr = open(os.devnull, 'w')
    text = text[:60] + "..." if len(text) > 60 else text
    toaster.show_toast(
        title,
        text,
        duration=2,
        threaded=True,
        callback_on_click=open_url
    )

def callback(full_event):
    event_id, event = full_event
    dict = {
        "EventId": event_id,
        "Event": event
    }
    event["EventHeader"]["EventDescriptor"]["Keyword"] = str(event["EventHeader"]["EventDescriptor"].get("Keyword", "0"))

    current_image = event.get("Image", "kjhfi").lower()
    current_parent_image = event.get("ParentImage", "kjhfi").lower()
    if current_image == AGENT_PATH or current_parent_image == AGENT_PATH or current_image in EXCLUDE_DIRS or current_parent_image in EXCLUDE_DIRS:
        return

    # hits = matcher.match(event) eski
    hits = analyze_log(event)
    if hits:
        print(hits[0]['title'], hits[0]['desc'])
        post_notification(hits[0]['title'], hits[0]['desc'])
    
    post(dict)


provider = ProviderInfo(
    'Microsoft-Windows-Sysmon',
    GUID("{5770385f-c22a-43e0-bf4c-06f5698ffbd9}")
)

etw = ETW(providers=[provider], event_callback=callback)
etw.start()

try:
    while True:
        time.sleep(2)
except:
    print("Agent to'xtadi")
    etw.stop()