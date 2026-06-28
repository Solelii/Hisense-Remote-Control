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
            # Make layer_app visible and on top
            (1, """
var el = document.querySelector('#layer_app');
el.style.display = 'block';
el.style.zIndex = '99999';
el.style.position = 'fixed';
el.style.top = '0';
el.style.left = '0';
el.style.width = '100%';
el.style.height = '100%';
'done';
"""),
            # Also try focusing the AppLayer component
            (2, """
var v = window.__vueTop.$children[0];
typeof v.$el.focus === 'function' ? v.$el.focus() : 'no focus';
"""),
            # Confirm current route of AppLayer
            (3, "window.__vueTop.$children[0].$route.path"),
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
