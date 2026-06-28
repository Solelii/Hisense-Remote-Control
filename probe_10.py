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
            # Find all event listeners on document
            (1, """
var listeners = [];
var orig = document.addEventListener;
JSON.stringify(typeof document.onkeydown);
"""),
            # Check what script files are loaded
            (2, """
var scripts = document.querySelectorAll('script');
var srcs = [];
for (var i = 0; i < scripts.length; i++) {
    srcs.push(scripts[i].src || scripts[i].innerHTML.substring(0, 100));
}
JSON.stringify(srcs);
"""),
            # Try KeyboardEvent with keyCode property override
            (3, """
var evt = new KeyboardEvent('keydown', {
    bubbles: true, cancelable: true,
    keyCode: 36, which: 36, key: 'Home'
});
Object.defineProperty(evt, 'keyCode', {value: 36});
document.dispatchEvent(evt);
evt.keyCode;
"""),
            # Try on window instead of document
            (4, """
var evt = new KeyboardEvent('keydown', {
    bubbles: true, cancelable: true,
    key: 'Home', keyCode: 36, which: 36
});
window.dispatchEvent(evt);
'sent to window';
"""),
            # Check h5vcc.system for any launch/navigate method
            (5, """
var sys = window.h5vcc.system;
JSON.stringify(Object.getOwnPropertyNames(sys));
"""),
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
