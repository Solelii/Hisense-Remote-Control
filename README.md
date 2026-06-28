# Hisense CDP Remote Control

Control a Hisense Smart TV from a Linux terminal with no physical remote, no app pairing, and no PIN — using the Chrome DevTools Protocol (CDP) exposed by the TV's own UI runtime.

---

## Background

This was built to solve a specific problem: a Hisense Smart TV isolated on a guest network with AP isolation enabled, no working remote, and no way to access the UI. The solution was discovered by systematically probing the TV's open ports and exploiting an unauthenticated CDP endpoint.

---

## How It Was Built — The Discovery Process

### Step 1: Network Reconnaissance

Standard ICMP ping and nmap discovery failed due to AP isolation. ARP-level scanning worked:

```bash
sudo nmap -sn 192.168.1.0/24
```

The TV was found at `192.168.1.35`. A full port scan revealed many open ports including `9222` — a well-known Chrome DevTools Protocol port.

### Step 2: CDP Endpoint Discovery

```bash
curl -s http://192.168.1.35:9222/json
```

This returned a JSON descriptor confirming an active CDP session:

```json
{
  "id": "cobalt",
  "title": "Cobalt",
  "type": "page",
  "url": "file:///html/hisenseUI/index.html#/LiveTV/",
  "webSocketDebuggerUrl": "ws://devtools/page/cobalt"
}
```

Key findings:
- The runtime is **Cobalt 12** (Google's embedded browser for TV apps), a very old QA build
- The page URL is `file:///html/hisenseUI/index.html` — the TV's own native UI, not a YouTube app
- The CDP endpoint is **completely unauthenticated**

### Step 3: Probing the Runtime

Connected via WebSocket and used `Runtime.evaluate` to execute JavaScript inside the TV's UI:

```python
import websocket, json
ws = websocket.create_connection("ws://192.168.1.35:9222/devtools/page/cobalt")
ws.send(json.dumps({
    "id": 1,
    "method": "Runtime.evaluate",
    "params": {"expression": "navigator.userAgent", "returnByValue": True}
}))
```

Confirmed:
- `window.h5vcc` exists (Cobalt's native API bridge) but keys are non-enumerable
- The DOM contains `data-v-*` attributes → the UI is built with **Vue.js**
- `document.body.innerHTML` showed layers: `#layer_app`, `#layer_module`, `#layer_system`

### Step 4: Finding the Vue Router

Scanned all DOM elements for `__vue__` instances:

```javascript
var els = document.querySelectorAll('*');
for (var i = 0; i < els.length; i++) {
    if (els[i].__vue__) { window.__vueRoot = els[i].__vue__; break; }
}
```

Then walked up the component tree to the root and confirmed `$router` was accessible:

```javascript
var v = window.__vueRoot;
while (v.$parent) { v = v.$parent; }
window.__vueTop = v;
// v.$router.currentRoute.path === "/"
```

Vue router navigation to `/Settings/Network` was accepted but produced no visible output — the `#layer_app` div was empty, meaning components weren't mounted in that layer.

### Step 5: Extracting the Keycode Map

Listed all loaded script files from the DOM:

```javascript
var scripts = document.querySelectorAll('script');
// Found: ./static/keyboard/js/constances.js, ./static/js/app.js, etc.
```

File reading via `fetch`, synchronous XHR, `file:///` XHR, and `Page.getResourceContent` all failed due to Cobalt's sandbox restrictions.

Instead, read constants directly from memory — the scripts were already executing and had exported to `window.CONST`:

```javascript
JSON.stringify(window.CONST.KEY)
```

This returned the TV's complete keycode map, including:

```json
{
  "VK_HOME": 36,
  "VK_MENU": 409,
  "VK_UP": 38, "VK_DOWN": 40, "VK_LEFT": 37, "VK_RIGHT": 39,
  "VK_ENTER": 13,
  "VK_VOLUME_UP": 411, "VK_VOLUME_DOWN": 412, "VK_MUTE": 413,
  "VK_LAUNCHER": 547,
  "VK_SOURCE": 505,
  ...
}
```

### Step 6: Key Injection

`Input.dispatchKeyEvent` (Chrome's CDP input method) is not implemented in Cobalt 12.

The working method uses `document.createEvent` with `Object.defineProperty` to force the correct `keyCode` and `which` values, firing both `keydown` and `keyup`:

```javascript
var e = document.createEvent('KeyboardEvent');
e.initKeyboardEvent('keydown', true, true, window, 0, 0, 0, 0, 409, 0);
Object.defineProperty(e, 'keyCode', {value: 409});
Object.defineProperty(e, 'which', {value: 409});
document.dispatchEvent(e);
```

This was confirmed working when volume change appeared on screen.

### Step 7: Building the Remote

Combined everything into an interactive terminal remote using Python's `tty`/`termios` for raw keyboard input, mapping terminal keypresses to TV keycodes and injecting them via CDP WebSocket.

---

## Requirements

```bash
pip install websocket-client
```

---

## Usage

```bash
python3 hisense_remote.py
```

The TV IP is hardcoded to `192.168.1.35` — edit `TV_WS` at the top of the script if yours differs.

### Controls

| Key | Action |
|-----|--------|
| Arrow keys | Navigate |
| Enter | OK / Select |
| `q` / ESC | Back |
| `h` | Home |
| `m` | Menu |
| `l` | Launcher |
| `s` | Source |
| `i` | Info |
| `+` / `-` | Volume Up / Down |
| `u` | Mute |
| `.` / `,` | Channel Up / Down |
| `p` / `x` | Play / Stop |
| `f` / `b` | Fast Forward / Rewind |
| `0`–`9` | Number keys |
| Ctrl+C | Quit |

---

## Limitations

- Tested only on Cobalt 12 (`/12.84472-qa`). Newer Hisense firmware may use a different runtime or lock down CDP.
- Key events are dispatched into the JS layer. If the TV's input handling sits below JS (e.g. in native Cobalt input), some keys may not respond.
- The CDP endpoint is unauthenticated on this firmware — this may not be the case on updated firmware.

---

## What Didn't Work (and Why)

| Approach | Reason it failed |
|----------|-----------------|
| `Input.dispatchKeyEvent` | Not implemented in Cobalt 12 |
| `fetch()` for file reading | Unhandled Promise rejection in Cobalt 12 |
| Synchronous XHR | `InvalidStateError` — blocked by Cobalt |
| `file:///` XHR | Security sandbox blocks it even from same origin |
| `Page.getResourceContent` | Not implemented in Cobalt 12 |
| `Debugger.getScriptSource` | No `scriptParsed` events emitted for pre-loaded scripts |
| Vue `$router.push()` | Router navigated but components didn't mount visibly |
| `initKeyboardEvent` alone | `keyCode` property is read-only without `defineProperty` override |