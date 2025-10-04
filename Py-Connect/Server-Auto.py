# server_with_close.py
import os
import sys
import socket
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog
import subprocess
import shutil
import json
import time

# ---------------- CONFIG / DEFAULTS ----------------
DEFAULT_CONFIG = {
    "bind_ip": "192.168.1.75",
    "port": 1957,
    "access_code": "1957",
    "hide_gui": True,
    "stop_flag_enabled": True,
    "stop_flag_path": os.path.join(os.path.expanduser("~"), "server_stop.flag")
}
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server_config.json")

ALLOWED_COMMANDS = {
    "ping_router": {"type": "shell", "cmd": ["ping", "-n" if os.name=="nt" else "-c","4","192.168.1.1"]},
    "get_ip": {"type": "func", "func": lambda: socket.gethostbyname(socket.gethostname())},
}

server_socket = None
running = False
clients = {}
ACCESS_CODE = None
config = {}

# ---------------- UTIL ----------------
def load_config():
    global config
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH,"r",encoding="utf-8") as f:
                config = json.load(f)
        except: config = DEFAULT_CONFIG.copy()
    else:
        config = DEFAULT_CONFIG.copy()
    for k,v in DEFAULT_CONFIG.items():
        if k not in config: config[k]=v
    return config

def save_config():
    global config
    try:
        with open(CONFIG_PATH,"w",encoding="utf-8") as f:
            json.dump(config,f,indent=2)
        log_output("[Config] Saved.")
        create_close_py()
        create_startup_bat()
    except Exception as e:
        log_output(f"[Config] Save failed: {e}")

def create_close_py():
    """Generates a self-destructing close.py to stop the server."""
    try:
        close_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "close.py")
        if not config.get("stop_flag_enabled", True):
            if os.path.exists(close_path): os.remove(close_path)
            return
        flag = config.get("stop_flag_path", DEFAULT_CONFIG["stop_flag_path"])
        contents = f"""\
import os, sys
flag_path = r\"{flag}\"
os.makedirs(os.path.dirname(flag_path), exist_ok=True)
with open(flag_path,"w",encoding="utf-8") as f: f.write("stop")
print(f"Stop flag created at {{flag_path}}")
try: os.remove(sys.argv[0]); print("close.py deleted itself")
except Exception as e: print("Failed to delete self:",e)
"""
        with open(close_path,"w",encoding="utf-8") as f: f.write(contents)
        log_output(f"[Helper] close.py generated at {close_path}")
    except Exception as e: log_output(f"[Helper] Failed to generate close.py: {e}")

def create_startup_bat():
    try:
        if os.name != "nt": return
        startup_dir = os.path.join(os.environ["APPDATA"], r"Microsoft\Windows\Start Menu\Programs\Startup")
        script_path = os.path.abspath(sys.argv[0])
        pythonw = shutil.which("pythonw.exe") or sys.executable
        bat_path = os.path.join(startup_dir, "run_server_with_close.bat")
        bat_contents = f'@echo off\r\n"{pythonw}" "{script_path}"\r\n'
        if not os.path.exists(bat_path) or open(bat_path,"r",encoding="utf-8",errors="ignore").read().strip()!=bat_contents.strip():
            with open(bat_path,"w",encoding="utf-8") as f: f.write(bat_contents)
            log_output(f"[Auto-start] Startup entry created at {bat_path}")
    except Exception as e:
        log_output(f"[Auto-start] Failed: {e}")

def try_hide_console():
    if os.name=="nt":
        try:
            import ctypes
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(),0)
        except: pass

def log_output(text):
    t = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {text}"
    try:
        log_box.config(state="normal")
        log_box.insert(tk.END, t+"\n")
        if auto_scroll_var.get(): log_box.see(tk.END)
        log_box.config(state="disabled")
    except: 
        try:
            with open(os.path.join(os.path.expanduser("~"),"server_with_close.log"),"a",encoding="utf-8") as f:
                f.write(t+"\n")
        except: pass

# ---------------- SERVER ----------------
def handle_client(conn, addr):
    ip, port = addr
    try:
        conn.send(b"Enter access code: ")
        code = conn.recv(1024).decode().strip()
        if code != ACCESS_CODE:
            conn.send(b"Wrong code. Disconnecting.")
            conn.close()
            return
        conn.send(b"Access granted. Allowed commands: " + ", ".join(ALLOWED_COMMANDS.keys()).encode()+b"\n")
        clients[conn] = addr
        update_client_list()
        log_output(f"[Connected] {ip}:{port}")

        while running:
            try:
                data = conn.recv(4096)
            except: break
            if not data: break
            token = data.decode().strip()
            if token.lower() in ("exit","quit"): break
            if token not in ALLOWED_COMMANDS:
                msg=f"Command '{token}' not allowed."
                conn.send(msg.encode())
                log_output(f"[{ip}] tried disallowed command: {token}")
                continue
            spec = ALLOWED_COMMANDS[token]
            try:
                if spec["type"]=="func": result=str(spec["func"]())
                elif spec["type"]=="shell":
                    proc=subprocess.Popen(spec["cmd"],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
                    out,_=proc.communicate(timeout=30)
                    result = out if out else "[OK]"
                else: result="[Unknown command type]"
            except Exception as e: result=f"[Error] {e}"
            conn.send(result.encode())
            log_output(f"[{ip}] > {token}\n{result}")

    except Exception as e:
        log_output(f"[Error] {ip}:{port} - {e}")
    finally:
        try: conn.close()
        except: pass
        clients.pop(conn,None)
        update_client_list()
        log_output(f"[Disconnected] {ip}:{port}")

def update_client_list():
    try:
        client_list.delete(0,tk.END)
        for conn,(ip,port) in clients.items(): client_list.insert(tk.END,f"{ip}:{port}")
    except: pass

def disconnect_selected_client():
    try:
        sel = client_list.curselection()
        if not sel: return
        idx=sel[0]
        conn=list(clients.keys())[idx]
        try: conn.send(b"exit"); conn.close()
        except: pass
        log_output(f"[Manually disconnected] {clients.get(conn,('?', '?'))[0]}")
    except Exception as e: messagebox.showerror("Error", str(e))

def clear_logs():
    try:
        log_box.config(state="normal")
        log_box.delete("1.0", tk.END)
        log_box.config(state="disabled")
    except: pass

def server_poll_stopflag():
    if not config.get("stop_flag_enabled", True): return False
    path=config.get("stop_flag_path", DEFAULT_CONFIG["stop_flag_path"])
    return os.path.exists(path)

def start_server_thread(): threading.Thread(target=start_server,daemon=True).start()

def start_server():
    global server_socket,running,ACCESS_CODE
    try:
        bind_ip = ip_entry.get().strip()
        port=int(port_entry.get())
        ACCESS_CODE = code_entry.get().strip()
        server_socket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
        server_socket.bind((bind_ip,port))
        server_socket.listen(5)
        running=True
        status_label.config(text=f"Server running on {bind_ip}:{port}",fg="green")
        log_output(f"[Server started on {bind_ip}:{port}]")
        start_btn.config(state="disabled")
        stop_btn.config(state="normal")
        server_socket.settimeout(1.0)
        while running:
            if server_poll_stopflag():
                log_output("[Stop flag detected] Shutting down server.")
                break
            try: conn,addr=server_socket.accept(); threading.Thread(target=handle_client,args=(conn,addr),daemon=True).start()
            except socket.timeout: continue
            except Exception as e: log_output(f"[Accept error] {e}"); break
    except Exception as e:
        messagebox.showerror("Server Error", str(e))
        status_label.config(text="Error",fg="orange")
    finally:
        running=False
        if server_socket: 
            try: server_socket.close()
            except: pass
        for c in list(clients.keys()):
            try: c.send(b"exit"); c.close()
            except: pass
        clients.clear()
        update_client_list()
        status_label.config(text="Server stopped",fg="red")
        log_output("[Server stopped]")
        start_btn.config(state="normal")
        stop_btn.config(state="disabled")

def stop_server_manual():
    if not config.get("stop_flag_enabled", True):
        global running,server_socket; running=False; 
        if server_socket: 
            try: server_socket.close()
            except: pass
        return
    path=config.get("stop_flag_path",DEFAULT_CONFIG["stop_flag_path"])
    try:
        os.makedirs(os.path.dirname(path),exist_ok=True)
        with open(path,"w",encoding="utf-8") as f: f.write("stop")
        log_output(f"[Manual] Created stop flag at {path}")
    except Exception as e: log_output(f"[Manual] Failed: {e}")

# ---------------- GUI ----------------
root=tk.Tk()
root.title("Server (with close.py)")
root.geometry("750x500")
load_config()

frame_top=tk.Frame(root); frame_top.pack(pady=6,fill="x")
tk.Label(frame_top,text="IP:").grid(row=0,column=0)
ip_entry=tk.Entry(frame_top,width=16); ip_entry.insert(0,config.get("bind_ip")); ip_entry.grid(row=0,column=1,padx=6)
tk.Label(frame_top,text="Port:").grid(row=0,column=2)
port_entry=tk.Entry(frame_top,width=6); port_entry.insert(0,str(config.get("port"))); port_entry.grid(row=0,column=3,padx=6)
tk.Label(frame_top,text="Access Code:").grid(row=0,column=4)
code_entry=tk.Entry(frame_top,width=12); code_entry.insert(0,config.get("access_code")); code_entry.grid(row=0,column=5,padx=6)
hide_var=tk.BooleanVar(value=config.get("hide_gui"))
tk.Checkbutton(frame_top,text="Hide GUI (background)",variable=hide_var).grid(row=0,column=6,padx=6)
tk.Label(frame_top,text="Stop Flag Enabled:").grid(row=1,column=0)
stopflag_var=tk.BooleanVar(value=config.get("stop_flag_enabled"))
tk.Checkbutton(frame_top,text="Enable",variable=stopflag_var).grid(row=1,column=1,padx=6)
tk.Label(frame_top,text="Stop Flag Path:").grid(row=1,column=2)
stopflag_entry=tk.Entry(frame_top,width=40); stopflag_entry.insert(0,config.get("stop_flag_path")); stopflag_entry.grid(row=1,column=3,columnspan=3,padx=6)
def browse_flag_path():
    p=filedialog.asksaveasfilename(title="Stop flag file",defaultextension="",initialfile=os.path.basename(stopflag_entry.get()))
    if p: stopflag_entry.delete(0,tk.END); stopflag_entry.insert(0,p)
tk.Button(frame_top,text="Browse...",command=browse_flag_path).grid(row=1,column=6,padx=6)
start_btn=tk.Button(frame_top,text="Start Server",command=start_server_thread); start_btn.grid(row=0,column=7,padx=6)
stop_btn=tk.Button(frame_top,text="Stop (create flag)",command=stop_server_manual,state="normal"); stop_btn.grid(row=1,column=7,padx=6)
save_btn=tk.Button(frame_top,text="Save Settings",command=lambda:on_save_settings()); save_btn.grid(row=2,column=7,padx=6,pady=4)
status_label=tk.Label(root,text="Stopped",fg="red"); status_label.pack()

frame_middle=tk.Frame(root); frame_middle.pack(fill="both",expand=True,padx=8)
client_frame=tk.Frame(frame_middle); client_frame.pack(side="left",fill="y",padx=6)
tk.Label(client_frame,text="Connected Clients").pack()
client_list=tk.Listbox(client_frame,width=28); client_list.pack(fill="y",expand=True)
tk.Button(client_frame,text="Disconnect Selected",command=disconnect_selected_client).pack(pady=6)
log_frame=tk.Frame(frame_middle); log_frame.pack(side="right",fill="both",expand=True)
tk.Label(log_frame,text="Command Logs").pack()
log_box=scrolledtext.ScrolledText(log_frame,state="disabled"); log_box.pack(fill="both",expand=True)

frame_bottom=tk.Frame(root); frame_bottom.pack(pady=6,fill="x")
auto_scroll_var=tk.BooleanVar(value=True)
tk.Checkbutton(frame_bottom,text="Auto-scroll",variable=auto_scroll_var).pack(side="left",padx=6)

theme_var=tk.StringVar(value="Light")
def toggle_theme(*_):
    if theme_var.get()=="Dark": root.configure(bg="#222"); log_box.configure(bg="#000",fg="#0f0"); client_list.configure(bg="#000",fg="#0f0")
    else: root.configure(bg="#eee"); log_box.configure(bg="#fff",fg="#000"); client_list.configure(bg="#fff",fg="#000")
tk.OptionMenu(frame_bottom,theme_var,"Light","Dark",command=toggle_theme).pack(side="left",padx=6)
tk.Button(frame_bottom,text="Clear Logs",command=clear_logs).pack(side="right",padx=6)

def on_save_settings():
    config["bind_ip"]=ip_entry.get().strip()
    try: config["port"]=int(port_entry.get().strip())
    except: messagebox.showerror("Invalid port","Port must be a number"); return
    config["access_code"]=code_entry.get().strip()
    config["hide_gui"]=hide_var.get()
    config["stop_flag_enabled"]=stopflag_var.get()
    config["stop_flag_path"]=stopflag_entry.get().strip() or DEFAULT_CONFIG["stop_flag_path"]
    save_config()
    messagebox.showinfo("Saved","Settings saved and close.py updated.")

def apply_hide_setting():
    if config.get("hide_gui",True): 
        try: root.withdraw()
        except: pass
    else: 
        try: root.deiconify()
        except: pass

def auto_start_actions():
    ip_entry.delete(0,tk.END); ip_entry.insert(0,config.get("bind_ip"))
    port_entry.delete(0,tk.END); port_entry.insert(0,str(config.get("port")))
    code_entry.delete(0,tk.END); code_entry.insert(0,config.get("access_code"))
    stopflag_entry.delete(0,tk.END); stopflag_entry.insert(0,config.get("stop_flag_path"))
    stopflag_var.set(config.get("stop_flag_enabled",True))
    hide_var.set(config.get("hide_gui",True))
    create_close_py(); create_startup_bat()
    root.after(800,start_server_thread)

def on_start():
    try_hide_console(); load_config(); apply_hide_setting(); root.after(100,auto_start_actions)

def on_close():
    if config.get("stop_flag_enabled",True):
        path=config.get("stop_flag_path",DEFAULT_CONFIG["stop_flag_path"])
        try: os.makedirs(os.path.dirname(path),exist_ok=True); open(path,"w",encoding="utf-8").write("stop")
        except: pass
    try: root.destroy()
    except: pass
    sys.exit(0)

root.protocol("WM_DELETE_WINDOW",on_close)
root.after(100,on_start)
root.mainloop()
