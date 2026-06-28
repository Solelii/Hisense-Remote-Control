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
            # Get the Vue root instance and its router
            (1, "typeof document.querySelector('#layer_app').__vue__"),
            (2, "typeof document.querySelector('#layer_app').__vue__.$router"),
            (3, "JSON.stringify(document.querySelector('#layer_app').__vue__.$router.currentRoute)"),

            # Try to navigate via Vue router
            (4, "document.querySelector('#layer_app').__vue__.$router.push('/Settings')"),
            (5, "document.querySelector('#layer_app').__vue__.$router.push('/Settings/Network')"),
        ]

        for cid, expr in probes:
            ws.send(json.dumps({
                "id": cid,
                "method": "Runtime.evaluate",
                "params": {"expression": expr, "returnByValue": True}
            }))
            time.sleep(1.0)

    threading.Thread(target=run).start()

ws = websocket.WebSocketApp(WS_URL, on_message=on_message, on_open=on_open)
ws.run_forever()
