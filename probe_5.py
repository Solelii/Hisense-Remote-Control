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
            # Scan all divs for __vue__ instance
            (1, """
var els = document.querySelectorAll('*');
var found = [];
for (var i = 0; i < els.length; i++) {
    if (els[i].__vue__) {
        found.push(els[i].id || els[i].className || els[i].tagName);
        if (found.length >= 5) break;
    }
}
JSON.stringify(found);
"""),
            # Try body and html directly
            (2, "typeof document.body.__vue__"),
            (3, "typeof document.documentElement.__vue__"),

            # Try layer_module which had the actual content
            (4, "typeof document.querySelector('#layer_module').__vue__"),
            (5, "typeof document.querySelector('#layer_system').__vue__"),
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
