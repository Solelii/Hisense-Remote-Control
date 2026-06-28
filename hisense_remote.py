#!/usr/bin/env python3
"""
Hisense TV Remote Control via Chrome DevTools Protocol (CDP)
Tested on Cobalt 12 / VIDAA - uses CONST.KEY keycodes from the TV's own constances.js
"""

import websocket
import json
import threading
import sys
import tty
import termios

TV_WS = "ws://192.168.1.35:9222/devtools/page/cobalt"

KEYS = {
    # Navigation
    "KEY_UP":       38,
    "KEY_DOWN":     40,
    "KEY_LEFT":     37,
    "KEY_RIGHT":    39,
    "KEY_ENTER":    13,
    "KEY_BACK":     27,   # VK_EXIT

    # Main buttons
    "KEY_HOME":     36,
    "KEY_MENU":     409,
    "KEY_LAUNCHER": 547,  # App launcher / home screen
    "KEY_SOURCE":   505,
    "KEY_INFO":     410,
    "KEY_TOOLS":    567,

    # Volume / Channel
    "KEY_VOL_UP":   411,
    "KEY_VOL_DOWN": 412,
    "KEY_MUTE":     413,
    "KEY_CH_UP":    415,
    "KEY_CH_DOWN":  416,

    # Media
    "KEY_PLAY":     424,
    "KEY_STOP":     425,
    "KEY_FFWD":     427,
    "KEY_FBKW":     428,

    # Color buttons
    "KEY_RED":      420,
    "KEY_GREEN":    421,
    "KEY_YELLOW":   422,
    "KEY_BLUE":     423,

    # Numbers
    "KEY_0": 48, "KEY_1": 49, "KEY_2": 50, "KEY_3": 51, "KEY_4": 52,
    "KEY_5": 53, "KEY_6": 54, "KEY_7": 55, "KEY_8": 56, "KEY_9": 57,

    # Apps
    "KEY_NETFLIX":  616,
    "KEY_YOUTUBE":  619,
    "KEY_AMAZON":   617,

    # Special
    "KEY_EPG":      405,
    "KEY_LIVETV":   556,
    "KEY_SUBTITLE": 518,
    "KEY_POWER":    400,
}

# Terminal keyboard -> TV key mapping
TERMINAL_MAP = {
    "\x1b[A": "KEY_UP",
    "\x1b[B": "KEY_DOWN",
    "\x1b[C": "KEY_RIGHT",
    "\x1b[D": "KEY_LEFT",
    "\r":     "KEY_ENTER",
    "\n":     "KEY_ENTER",
    "\x1b":   "KEY_BACK",
    "q":      "KEY_BACK",
    "h":      "KEY_HOME",
    "m":      "KEY_MENU",
    "i":      "KEY_INFO",
    "+":      "KEY_VOL_UP",
    "-":      "KEY_VOL_DOWN",
    "u":      "KEY_MUTE",
    ".":      "KEY_CH_UP",
    ",":      "KEY_CH_DOWN",
    "s":      "KEY_SOURCE",
    "l":      "KEY_LAUNCHER",
    "t":      "KEY_TOOLS",
    "e":      "KEY_EPG",
    "v":      "KEY_LIVETV",
    "p":      "KEY_PLAY",
    "x":      "KEY_STOP",
    "f":      "KEY_FFWD",
    "b":      "KEY_FBKW",
    "1":      "KEY_1", "2": "KEY_2", "3": "KEY_3",
    "4":      "KEY_4", "5": "KEY_5", "6": "KEY_6",
    "7":      "KEY_7", "8": "KEY_8", "9": "KEY_9",
    "0":      "KEY_0",
}

ws_conn = None
msg_id = 0
lock = threading.Lock()

def send_key(key_name):
    global msg_id
    keycode = KEYS.get(key_name)
    if keycode is None:
        return

    expr = f"""
(function() {{
    var e = document.createEvent('KeyboardEvent');
    e.initKeyboardEvent('keydown', true, true, window, 0, 0, 0, 0, {keycode}, 0);
    Object.defineProperty(e, 'keyCode', {{value: {keycode}}});
    Object.defineProperty(e, 'which', {{value: {keycode}}});
    document.dispatchEvent(e);

    var e2 = document.createEvent('KeyboardEvent');
    e2.initKeyboardEvent('keyup', true, true, window, 0, 0, 0, 0, {keycode}, 0);
    Object.defineProperty(e2, 'keyCode', {{value: {keycode}}});
    Object.defineProperty(e2, 'which', {{value: {keycode}}});
    document.dispatchEvent(e2);
    return '{key_name}:{keycode}';
}})()
"""
    with lock:
        msg_id += 1
        mid = msg_id
    ws_conn.send(json.dumps({
        "id": mid,
        "method": "Runtime.evaluate",
        "params": {"expression": expr, "returnByValue": True}
    }))

def on_message(ws, message):
    # Silent — only print errors
    msg = json.loads(message)
    if msg.get("result", {}).get("wasThrown"):
        err = msg["result"]["result"].get("description", "")
        print(f"\r[CDP error] {err}")

def on_error(ws, error):
    print(f"\r[WS error] {error}")

def on_close(ws, *args):
    print("\r[Disconnected]")

def on_open(ws):
    print("\r[Connected to TV]")

def print_help():
    print("""
╔══════════════════════════════════════════╗
║     Hisense CDP Remote Control           ║
╠══════════════════════════════════════════╣
║  Arrow keys : Navigate                   ║
║  Enter      : OK/Select                  ║
║  q / ESC    : Back                       ║
║  h          : Home                       ║
║  m          : Menu                       ║
║  l          : Launcher                   ║
║  s          : Source                     ║
║  i          : Info                       ║
║  t          : Tools                      ║
║  e          : EPG                        ║
║  v          : Live TV                    ║
║  + / -      : Volume Up/Down             ║
║  u          : Mute                       ║
║  . / ,      : Channel Up/Down            ║
║  p          : Play                       ║
║  x          : Stop                       ║
║  f / b      : Fast Fwd / Fast Bkw        ║
║  0-9        : Number keys                ║
║  Ctrl+C     : Quit remote                ║
╚══════════════════════════════════════════╝
""")

def read_key():
    """Read a keypress from terminal, handling escape sequences."""
    ch = sys.stdin.read(1)
    if ch == "\x1b":
        # Could be escape sequence
        try:
            ch2 = sys.stdin.read(1)
            if ch2 == "[":
                ch3 = sys.stdin.read(1)
                return "\x1b[" + ch3
            else:
                return "\x1b"
        except:
            return "\x1b"
    return ch

def main():
    global ws_conn

    print("Connecting to TV at", TV_WS)

    ws_conn = websocket.WebSocketApp(
        TV_WS,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )

    wst = threading.Thread(target=ws_conn.run_forever)
    wst.daemon = True
    wst.start()

    import time
    time.sleep(1.5)

    print_help()
    print("Press keys to control TV (Ctrl+C to quit):\n")

    # Save terminal settings
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    try:
        tty.setraw(fd)
        while True:
            ch = read_key()

            if ch == "\x03":  # Ctrl+C
                break

            key_name = TERMINAL_MAP.get(ch)
            if key_name:
                send_key(key_name)
                # Show feedback
                sys.stdout.write(f"\r> {key_name} ({KEYS[key_name]})          \r")
                sys.stdout.flush()
            else:
                sys.stdout.write(f"\r> (unknown key: {repr(ch)})    \r")
                sys.stdout.flush()

    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        print("\nDisconnecting...")
        ws_conn.close()

if __name__ == "__main__":
    main()
