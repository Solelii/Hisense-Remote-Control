import websocket
import json
import threading
import time

WS_URL = "ws://192.168.1.35:9222/devtools/page/cobalt"
results = {}

def on_message(ws, message):
    msg = json.loads(message)
    print(json.dumps(msg, indent=2))

def on_open(ws):
    def run():
        cmd_id = 1

        probes = [
            # What JS globals exist?
            ("navigator.userAgent", cmd_id),
            ("typeof window.h5vcc", cmd_id + 1),        # Cobalt-specific API
            ("typeof window.h5vcc?.system", cmd_id + 2),
            ("JSON.stringify(Object.keys(window.h5vcc || {}))", cmd_id + 3),
            ("navigator.onLine", cmd_id + 4),
            ("window.location.href", cmd_id + 5),
        ]

        for expr, cid in probes:
            ws.send(json.dumps({
                "id": cid,
                "method": "Runtime.evaluate",
                "params": {"expression": expr, "returnByValue": True}
            }))
            time.sleep(0.5)

    threading.Thread(target=run).start()

ws = websocket.WebSocketApp(WS_URL, on_message=on_message, on_open=on_open)
ws.run_forever()
