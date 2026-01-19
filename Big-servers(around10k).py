import websocket
import json
import time
import threading
import pandas as pd
import string
from queue import Queue

# --- CONFIGURATION ---
TOKEN = "YOUR_DISCORD_TOKEN"
GUILD_ID = "YOUR_TARGET_SERVER"
OUTPUT_FILE = "NAME_OF_TARGET_SERVER.xlsx"

captured_members = {}
ADMIN_ROLE_IDS = set()
STAFF_ROLE_IDS = set()
VC_MOD_ROLE_IDS = set()
LAST_QUERY = "" 

# --- DATA HANDLING ---
data_queue = Queue()
lock = threading.Lock()

# --- CHARACTER SETS ---
NUMBERS = string.digits
SYMBOLS = " !@#$%^&*()_+{}[]|\\:;\"'<>,?/「」『』【】★._-"
LATIN_BASE = string.ascii_lowercase + "._-"
ARABIC_RANGE = [chr(i) for i in range(0x0621, 0x064B)]

def is_arabic(text):
    """Detects Arabic characters in provided text."""
    if not text: return False
    return any('\u0600' <= char <= '\u06FF' for char in text)

def is_staff(member_roles):
    if any(r in ADMIN_ROLE_IDS for r in member_roles): return "Admin"
    if any(r in STAFF_ROLE_IDS for r in member_roles): return "Staff"
    if any(r in VC_MOD_ROLE_IDS for r in member_roles): return "VC Mod"
    return "Regular Member"

def worker():
    """Processes members from the queue to prevent gateway lag."""
    while True:
        members = data_queue.get()
        if members is None: break
        
        with lock:
            for m in members:
                u = m['user']
                if u['id'] not in captured_members:
                    username = u['username']
                    display = m.get('nick') or u.get('global_name') or ""
                    roles = m.get('roles', [])
                    m_type = "Bot" if u.get('bot', False) else is_staff(roles)
                    
                    captured_members[u['id']] = {
                        "Username": username, 
                        "Display": display,
                        "User ID": str(u['id']), 
                        "Type": m_type,
                        "Role IDs": ",".join(roles)
                    }
                    
                    if is_arabic(username + display):
                        print(f"[{time.strftime('%H:%M:%S')}] Arabic Member Found: {username} ({display})")
                    else:
                        print(f"[{time.strftime('%H:%M:%S')}] Member Found: {username}")
                        
        data_queue.task_done()

def on_open(ws):
    print(f"[{time.strftime('%H:%M:%S')}] [!] Connection Established. Identifying...")
    auth = {
        "op": 2,
        "d": {
            "token": TOKEN,
            "capabilities": 16381,
            "intents": 32509,
            "properties": {"os": "Windows", "browser": "Chrome", "device": ""},
            "presence": {"status": "online", "afk": False},
            "compress": False
        }
    }
    ws.send(json.dumps(auth))

def on_message(ws, message):
    data = json.loads(message)
    
    if data.get('op') == 10:
        interval = data['d']['heartbeat_interval'] / 1000
        threading.Thread(target=heartbeat, args=(ws, interval), daemon=True).start()

    if data.get('t') == "READY":
        print(f"[{time.strftime('%H:%M:%S')}] [READY] Logged in as: {data['d']['user']['username']}")
        for guild in data['d'].get('guilds', []):
            if guild['id'] == GUILD_ID:
                for role in guild.get('roles', []):
                    p = int(role.get('permissions', 0))
                    if (p & 0x8) == 0x8: ADMIN_ROLE_IDS.add(role['id'])
                    elif (p & 0x2000) == 0x2000 or (p & 0x2) == 0x2 or (p & 0x4) == 0x4: STAFF_ROLE_IDS.add(role['id'])
                    elif (p & 0x400000) == 0x400000 or (p & 0x800000) == 0x800000: VC_MOD_ROLE_IDS.add(role['id'])
        
        threading.Thread(target=start_scraping, args=(ws,), daemon=True).start()

    if data.get('t') == "GUILD_MEMBERS_CHUNK":
        data_queue.put(data['d'].get('members', []))

def heartbeat(ws, interval):
    while True:
        time.sleep(interval)
        try: ws.send(json.dumps({"op": 1, "d": None}))
        except: break

def start_scraping(ws):
    global LAST_QUERY
    try:
        # Phase 0: Broad Fetch
        print("[*] Phase 0: Requesting Broad Chunks...")
        send_query(ws, "", limit=0)
        time.sleep(5)
        save_to_excel()

        # Phase 1: Arabic Character Scan
        print("[*] Phase 1: Arabic Character Specific Scan...")
        for char in ARABIC_RANGE:
            send_query(ws, char, limit=100)
        save_to_excel()

        # Phase 2: Numeric
        print("[*] Phase 2: Numeric Single-Character...")
        for char in NUMBERS:
            send_query(ws, char)
        save_to_excel()

        # Phase 3: Symbols
        print("[*] Phase 3: Symbol Single-Character...")
        for char in SYMBOLS:
            send_query(ws, char)
        save_to_excel()

        # Phase 4: Latin Triple-Character
        print("[*] Phase 4: Latin Two-Character...")
        for first in LATIN_BASE:
            for second in LATIN_BASE:
                    query = first + second
                    if query <= LAST_QUERY: 
                        continue 
                    
                    LAST_QUERY = query
                    send_query(ws, query)
            # Save after completing a 'first' letter cycle
            save_to_excel()
            
        print(f"\n[SUCCESS] Final count: {len(captured_members)}")
    except Exception as e:
        print(f"[ERROR in Scraping Thread] {e}")

def send_query(ws, query, limit=100):
    try:
        payload = {
            "op": 8, 
            "d": {
                "guild_id": GUILD_ID, 
                "query": query, 
                "limit": limit,
                "nonce": str(time.time())
            }
        }
        ws.send(json.dumps(payload, ensure_ascii=False))
        time.sleep(0.80)
    except: pass

def save_to_excel():
    with lock:
        if captured_members:
            try:
                pd.DataFrame(list(captured_members.values())).to_excel(OUTPUT_FILE, index=False)
                print(f"[*] Snapshot saved. Total members: {len(captured_members)}")
            except Exception as e:
                print(f"[!] Save failed: {e}")

def run_ws():
    threading.Thread(target=worker, daemon=True).start()
    while True:
        try:
            ws = websocket.WebSocketApp(
                "wss://gateway.discord.gg/?v=9&encoding=json",
                on_open=on_open,
                on_message=on_message,
                on_error=lambda ws, err: print(f"[GATEWAY ERROR] {err}"),
                on_close=lambda ws, code, msg: print(f"[!] Connection Closed ({code}).")
            )
            ws.run_forever()
        except Exception as e:
            print(f"[CRITICAL ERROR] {e}")
        time.sleep(5)

if __name__ == "__main__":
    run_ws()