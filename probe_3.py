import websocket
import json
import threading
import time

WS_URL = "ws://192.168.1.35:9222/devtools/page/cobalt"

def on_message(ws, message):
    print(json.dumps(json.loads(message), indent=2))

def on_open(ws):
    def run():
        probes = [
            # What does the current DOM look like?
            (1, "document.title"),
            (2, "document.body.innerHTML.substring(0, 500)"),

            # Look for a router object
            (3, "typeof window.app"),
            (4, "typeof window.router"),
            (5, "typeof window.Angular"),
            (6, "typeof window.Vue"),
            (7, "typeof window.React"),

            # Try common SPA router navigation calls
            (8, "typeof window.navigate"),
            (9, "typeof window.goToSettings"),
        ]

        for cid, expr in probes:
            ws.send(json.dumps({
                "id": cid,
                "method": "Runtime.evaluate",
                "params": {"expression": expr, "returnByValue": True}
            }))
            time.sleep(0.5)

    threading.Thread(target=run).start()

ws = websocket.WebSocketApp(WS_URL, on_message=on_message, on_open=on_open)
ws.run_forever()
