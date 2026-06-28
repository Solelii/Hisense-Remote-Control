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
            # Get the first Vue instance found
            (1, """
var els = document.querySelectorAll('*');
for (var i = 0; i < els.length; i++) {
    if (els[i].__vue__) {
        window.__vueRoot = els[i].__vue__;
        break;
    }
}
typeof window.__vueRoot;
"""),
            # Walk up to find the root with $router
            (2, """
var v = window.__vueRoot;
var depth = 0;
while (v.$parent && depth < 20) { v = v.$parent; depth++; }
window.__vueTop = v;
typeof v.$router;
"""),
            # If router found, get current route
            (3, "JSON.stringify(window.__vueTop.$router.currentRoute)"),

            # Navigate to settings
            (4, "window.__vueTop.$router.push('/Settings')"),
            (5, "window.__vueTop.$router.push('/Settings/Network')"),
        ]

        for cid, expr in probes:
            ws.send(json.dumps({
                "id": cid,
                "method": "Runtime.evaluate",
                "params": {"expression": expr, "returnByValue": True}
            }))
            time.sleep(1.2)

    threading.Thread(target=run).start()

ws = websocket.WebSocketApp(WS_URL, on_message=on_message, on_open=on_open)
ws.run_forever()
