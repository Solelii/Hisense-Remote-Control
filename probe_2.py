import websocket
import json
import threading
import time

WS_URL = "ws://192.168.1.35:9222/devtools/page/cobalt"

def on_message(ws, message):
    msg = json.loads(message)
    print(json.dumps(msg, indent=2))

def on_open(ws):
    def run():
        probes = [
            # Probe h5vcc without optional chaining
            (1,  "typeof window.h5vcc.system"),
            (2,  "typeof window.h5vcc.network"),
            (3,  "typeof window.h5vcc.storage"),
            (4,  "typeof window.h5vcc.settings"),

            # Try to read h5vcc.system properties directly
            (5,  "window.h5vcc.system.getPlatformName()"),
            (6,  "window.h5vcc.system.getFirmwareVersion()"),

            # The UI is file-based — can we read the filesystem?
            (7,  "typeof window.h5vcc.fileSystem"),

            # Navigate the UI to network settings directly
            (8,  "window.location.hash = '#/Settings/Network'"),
            (9,  "window.location.hash = '#/Settings/'"),
        ]

        for cid, expr in probes:
            ws.send(json.dumps({
                "id": cid,
                "method": "Runtime.evaluate",
                "params": {"expression": expr, "returnByValue": True}
            }))
            time.sleep(0.8)

    threading.Thread(target=run).start()

ws = websocket.WebSocketApp(WS_URL, on_message=on_message, on_open=on_open)
ws.run_forever()
