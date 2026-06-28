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
            # Find ALL vue roots (elements with __vue__ but no $parent)
            (1, """
var els = document.querySelectorAll('*');
var roots = [];
for (var i = 0; i < els.length; i++) {
    var v = els[i].__vue__;
    if (v && !v.$parent) {
        roots.push({
            id: els[i].id,
            cls: els[i].className,
            hasRouter: typeof v.$router,
            route: v.$router ? v.$router.currentRoute.path : null
        });
    }
}
JSON.stringify(roots);
"""),
            # Also check what $children the top vue has
            (2, """
var v = window.__vueTop;
JSON.stringify(v.$children.map(function(c) {
    return { name: c.$options.name, route: c.$route ? c.$route.path : null };
}));
"""),
            # Try navigating via key event simulation instead
            (3, """
var evt = new KeyboardEvent('keydown', {keyCode: 72, key: 'Home', bubbles: true});
document.dispatchEvent(evt);
'sent';
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
