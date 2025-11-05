# server_autostart.py
import os
import socket
import threading
import sys
import time
import traceback

# Optional tray support
try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except Exception:
    TRAY_AVAILABLE = False

# Hide console on Windows (attempt)
if os.name == "nt":
    try:
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except Exception:
        pass

# ---------------- Configuration (auto-start values) ----------------
BIND_IP = "192.168.1.124"
BIND_PORT = 2357
ACCESS_CODE = "2357"
# ------------------------------------------------------------------

server_socket = None
running = False
clients = {}  # {conn: (ip, port)}
lock = threading.Lock()

# Minimal logger (thread-safe) that also stores a small circular history
_log_history = []
_LOG_HISTORY_MAX = 200

def log(text):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp}  {text}"
    with lock:
        _log_history.append(line)
        if len(_log_history) > _LOG_HISTORY_MAX:
            _log_history.pop(0)
    # Also print to stdout for debugging (console may be hidden)
    try:
        print(line)
    except:
        pass

def get_log_text():
    with lock:
        return "\n".join(_log_history)

# ---------------- Networking / Client handling (unchanged behavior) ----------------
def handle_client(conn, addr):
    ip, port = addr
    try:
        conn.send(b"Enter access code: ")
        code = conn.recv(1024).decode(errors="ignore").strip()
        if code != ACCESS_CODE:
            try:
                conn.send(b"Wrong code. Disconnecting.")
            except:
                pass
            conn.close()
            log(f"[Auth Failed] {ip}:{port}")
            return
        try:
            conn.send(b"Access granted. Ready.\n")
        except:
            pass

        with lock:
            clients[conn] = addr
        log(f"[Connected] {ip}:{port}")

        while True:
            data = conn.recv(4096)
            if not data:
                break
            cmd = data.decode(errors="ignore")
            if cmd.strip().lower() == "exit":
                break
            # execute command, same as original behavior
            try:
                output = os.popen(cmd).read()
            except Exception as e:
                output = f"[Execution error] {e}"
            if not output:
                output = "[Command executed]"
            try:
                conn.send(output.encode(errors="ignore"))
            except Exception:
                # Broken pipe / client disconnected
                break
            log(f"[{ip}] > {cmd.strip()}\n{(output[:1000] + '...') if len(output)>1000 else output}")

    except Exception as e:
        log(f"[Error] {ip}:{port} - {e}")
        try:
            traceback.print_exc()
        except:
            pass
    finally:
        try:
            conn.close()
        except:
            pass
        with lock:
            clients.pop(conn, None)
        log(f"[Disconnected] {ip}:{port}")

def stop_server():
    global running, server_socket
    log("[Stopping server]")
    running = False
    try:
        if server_socket:
            server_socket.close()
    except:
        pass
    # disconnect clients
    with lock:
        for conn in list(clients.keys()):
            try:
                conn.send(b"exit")
                conn.close()
            except:
                pass
        clients.clear()
    log("[Server stopped]")

def server_accept_loop(bind_ip, bind_port):
    global server_socket, running
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((bind_ip, bind_port))
        server_socket.listen(5)
        running = True
        log(f"[Server started on {bind_ip}:{bind_port}] (access code: {ACCESS_CODE})")
    except Exception as e:
        log(f"[Server Error] Failed to bind {bind_ip}:{bind_port} -> {e}")
        return

    while running:
        try:
            conn, addr = server_socket.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
        except Exception as e:
            if running:
                log(f"[Accept loop error] {e}")
            break

# ---------------- Tray icon (optional) ----------------
def create_image_for_tray():
    # small simple square icon generated at runtime
    img = Image.new('RGB', (64, 64), color=(0, 0, 0))
    d = ImageDraw.Draw(img)
    # draw a simple lightning-like shape
    d.polygon([(10,10),(40,10),(22,34),(54,34),(14,60),(26,36),(10,36)], fill=(255, 200, 0))
    return img

_tray_icon = None

def on_tray_show_logs(icon, item):
    # write logs to a temp file and open with default editor, or print to console fallback
    try:
        import tempfile, webbrowser
        tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log", encoding="utf-8")
        tmp.write(get_log_text())
        tmp.close()
        webbrowser.open(tmp.name)
    except Exception:
        # fallback: print top lines
        print("=== SERVER LOG ===")
        print(get_log_text())
        print("==================")

def on_tray_stop_server(icon, item):
    stop_server()

def on_tray_exit(icon, item):
    stop_server()
    try:
        icon.stop()
    except:
        pass
    # try to kill process gently
    try:
        os._exit(0)
    except:
        sys.exit(0)

def start_tray():
    global _tray_icon
    if not TRAY_AVAILABLE:
        log("[Tray support not available: install pystray + pillow to enable]")
        return
    try:
        image = create_image_for_tray()
        menu = pystray.Menu(
            pystray.MenuItem("Show Logs", on_tray_show_logs),
            pystray.MenuItem("Stop Server", on_tray_stop_server),
            pystray.MenuItem("Exit", on_tray_exit)
        )
        _tray_icon = pystray.Icon("remote_server", image, "RemoteServer", menu)
        # Run tray in its own thread (pystray.run is blocking)
        threading.Thread(target=_tray_icon.run, daemon=True).start()
        log("[Tray icon started]")
    except Exception as e:
        log(f"[Tray start error] {e}")

# ---------------- Main auto-start behavior ----------------
def main():
    # immediate auto-start
    threading.Thread(target=server_accept_loop, args=(BIND_IP, BIND_PORT), daemon=True).start()

    # attempt tray
    start_tray()

    # Keep the main thread alive indefinitely; prevents auto-close
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("[KeyboardInterrupt] Shutting down")
        stop_server()
    except Exception as e:
        log(f"[Main loop exception] {e}")
        stop_server()
    finally:
        # Prevent instant closure on errors
        log("[Server terminated. Press Enter to close...]")
        input()

if __name__ == "__main__":
    main()
