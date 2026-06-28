import websocket
import json
import threading
import time

WS_URL = "ws://192.168.1.35:9222/devtools/page/cobalt"

def on_message(ws, message):
    print(json.dumps(json.loads(message), indent=2))

def on_open(ws):
    def run():
        # TV remote keycodes (RC standard)
        keys = [
            (1,  36,  "Home"),
            (2,  27,  "Escape/Back"),
            (3,  403, "Red button"),
            (4,  122, "F11/Menu"),
            (5,  457, "Info"),
            (6,  461, "Back/Return"),
        ]

        for cid, code, name in keys:
            expr = """
var e = document.createEvent('KeyboardEvent');
e.initKeyboardEvent('keydown', true, true, window, 0, 0, 0, 0, {code}, 0);
document.dispatchEvent(e);
'{name}';
""".replace("{code}", str(code)).replace("{name}", name)
            ws.send(json.dumps({
                "id": cid,
                "method": "Runtime.evaluate",
                "params": {"expression": expr, "returnByValue": True}
            }))
            time.sleep(1.5)

    threading.Thread(target=run).start()

ws = websocket.WebSocketApp(WS_URL, on_message=on_message, on_open=on_open)
ws.run_forever()
