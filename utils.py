import os
import json
import time

def plugin_root():
    path = os.environ.get(
        "DGHUB_PLUGIN_ROOT", 
        os.path.dirname(os.path.abspath(__file__))
        )
    return path

def load_manifest(path):
    with open(os.path.join(path, 'manifest.json'), 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    return manifest

async def send_change_log(ws, msg):
    payload = "[dgGmod] " + msg.get("key", "") + ":  " + str(msg.get("value", ""))
    try:
        await ws.send(
            json.dumps(
                {
                    "op": "log",
                    "level": "info",
                    "message": payload
                },
            ensure_ascii=False
            )
        ) 
    except Exception:
        pass

async def send_log(ws, data, log_type="info"):
    if log_type == "error":
        data = f"[dgGmod] {data!r}"
    try:
        await ws.send(
            json.dumps(
                {
                    "op": "log",
                    "level": log_type,
                    "message": data
                },
            ensure_ascii=False
            )
        )  
    except Exception:
        pass

class Logger:
    def __init__(self):
        self.file = "error.log"
        self.isfull = False

    def getTime(self):
        return time.strftime("%Y-%m-%d %H:%M:%S")

    def checkFull(self):
        if os.path.getsize(self.file) > 1024*1024:
            self.isfull = True
        else:
            self.isfull = False

    def log(self, data, log_type="info", error_trace=""):
        self.checkFull()
        if self.isfull:
            self.clearLogFile()
        try:
            with open(self.file, "a", encoding="utf-8") as f:
                if log_type == "error":
                    f.write(f"{self.getTime()} {error_trace}\n")
                else:
                    f.write(f"{self.getTime()} {data}\n")
        except Exception:
            pass

    def clearLogFile(self):
        self.isfull = False
        try:
            with open(self.file, "w", encoding="utf-8") as f:
                pass
        except Exception:
            pass
