import re
import psycopg
import os
import docker
import threading
import time

# --- KONFIGURATION ---
DB_HOST = 'postgres_db' 
DB_NAME = 'fishtest'
DB_TABLE = 'fishtest'
DB_USER = 'admin'
DB_PASS = 'passwort'

WORKER_PREFIX = "fishtest-worker"
LOG_PATTERN = r"Finished game (?P<log_id>\d+) \((?P<white>.*?) vs (?P<black>.*?)\): (?P<res>[\d/1-]+) \{(?P<reason>.*)\}"

# Finished game 62 (Base-b3a810a1c4 vs New-9cf4e41d1b): 1/2-1/2 {Draw by 3-fold repetition} 
# Finished game 47 (New-9cf4e41d1b vs Base-b3a810a1c4): 1-0 {White wins by adjudication}
# Finished game 63 (New-db0fea68e7 vs Base-b3a810a1c4): 1-0 {White mates}
# Finished game 60 (Base-b3a810a1c4 vs New-db0fea68e7): 1/2-1/2 {Draw by insufficient mating material}
# Finished game 46 (Base-b3a810a1c4 vs New-9cf4e41d1b): 1/2-1/2 {Draw by stalemate}


def get_clean_reason(raw_reason):
    text = raw_reason.lower()
    prefixes = ["white wins by ", "black wins by ", "draw by ", "white ", "black ", "draw "]
    for p in prefixes:
        text = text.replace(p, "")
    text = text.strip()
    return "mate" if text == "mates" else text

def stream_container_logs(container_name):
    """Überwacht fishtest-worker"""
    print(f"[*] Überwachung : {container_name}")
    client = docker.from_env()
    
    # Puffer für unvollständige Zeilen
    buffer = ""

    try:
        container = client.containers.get(container_name)
        conn = psycopg.connect(host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASS)
        conn.autocommit = True
        cur = conn.cursor()

        # stream=True nur einzelne zeichen
        for chunk in container.logs(stream=True, follow=True, tail=0):
            # 1
            buffer += chunk.decode('utf-8', errors='ignore')

            # 2
            while "\n" in buffer:
                line_str, buffer = buffer.split("\n", 1)
                line_str = line_str.strip()

                if not line_str:
                    continue

                # fehler  lesen
                # print(f"DEBUG: {container_name} sagt: {line_str}", flush=True) 

                match = re.search(LOG_PATTERN, line_str)
                if match:
                    data = match.groupdict()
                    win = "white" if data["res"] == "1-0" else "black" if data["res"] == "0-1" else "draw"
                    clean_reason = get_clean_reason(data["reason"])

                    cur.execute("""
                        INSERT INTO {DB_TABLE} 
                        (container_name, log_game_id, white_engine, black_engine, win, termination_reason) 
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (container_name, int(data["log_id"]), data["white"], data["black"], win, clean_reason))
                    print(f"[DB] {container_name} -> Spiel {data['log_id']} gespeichert.", flush=True)

    except Exception as e:
        print(f"[!] Fehler bei {container_name}: {e}")
    finally:
        if 'conn' in locals(): conn.close()


def main():
    client = docker.from_env()
    monitored_containers = set()

    print(f"[*] Fishtest-Master-Importer aktiv. Suche nach '{WORKER_PREFIX}*'")

    while True:
        try:
            # Liste auf
            current_containers = client.containers.list()
            
            for container in current_containers:
                if container.name.startswith(WORKER_PREFIX) and container.name not in monitored_containers:
                    # Starte einen Thread für jeden neuen Worker
                    t = threading.Thread(target=stream_container_logs, args=(container.name,), daemon=True)
                    t.start()
                    monitored_containers.add(container.name)
            
            # lösche liste
            running_names = [c.name for c in current_containers]
            monitored_containers = {name for name in monitored_containers if name in running_names}

        except Exception as e:
            print(f"[Scanner-Fehler] {e}")
            
        time.sleep(10) 

if __name__ == "__main__":
    main()
