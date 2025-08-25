# server_gui_full.py
import os
import socket
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext

# Hide console on Windows
if os.name == "nt":
    try:
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except:
        pass

# --- Global variables ---
server_socket = None
running = False
clients = {}  # {conn: (ip, port)}
PORT = 9999
ACCESS_CODE = "1234"

# --- FUNCTIONS ---
def log_output(text):
    log_box.config(state="normal")
    log_box.insert(tk.END, text + "\n")
    if auto_scroll_var.get():
        log_box.see(tk.END)
    log_box.config(state="disabled")

def toggle_theme():
    if theme_var.get() == "Dark":
        root.configure(bg="#222")
        log_box.configure(bg="#000", fg="#0f0")
        client_list.configure(bg="#000", fg="#0f0")
    else:
        root.configure(bg="#eee")
        log_box.configure(bg="#fff", fg="#000")
        client_list.configure(bg="#fff", fg="#000")

def handle_client(conn, addr):
    ip, port = addr
    try:
        conn.send(b"Enter access code: ")
        code = conn.recv(1024).decode().strip()
        if code != ACCESS_CODE:
            conn.send(b"Wrong code. Disconnecting.")
            conn.close()
            return
        conn.send(b"Access granted. Ready.\n")
        clients[conn] = addr
        update_client_list()
        log_output(f"[Connected] {ip}:{port}")

        while True:
            cmd = conn.recv(4096).decode()
            if not cmd or cmd.lower() == "exit":
                break
            output = os.popen(cmd).read()
            if not output:
                output = "[Command executed]"
            conn.send(output.encode())
            log_output(f"[{ip}] > {cmd}\n{output}")

    except Exception as e:
        log_output(f"[Error] {ip}:{port} - {e}")
    finally:
        conn.close()
        clients.pop(conn, None)
        update_client_list()
        log_output(f"[Disconnected] {ip}:{port}")

def start_server():
    global server_socket, running, PORT, ACCESS_CODE
    try:
        PORT = int(port_entry.get())
        ACCESS_CODE = code_entry.get().strip()
        server_socket = socket.socket()
        server_socket.bind(("0.0.0.0", PORT))
        server_socket.listen()
        running = True
        status_label.config(text=f"Server running on port {PORT}", fg="green")
        log_output(f"[Server started on port {PORT}]")
        start_btn.config(state="disabled")
        stop_btn.config(state="normal")

        while running:
            try:
                conn, addr = server_socket.accept()
                threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
            except Exception as e:
                break
    except Exception as e:
        messagebox.showerror("Server Error", str(e))
        status_label.config(text="Error", fg="orange")

def stop_server():
    global running, server_socket, clients
    running = False
    if server_socket:
        try:
            server_socket.close()
        except:
            pass
    for conn in list(clients.keys()):
        try:
            conn.send(b"exit")
            conn.close()
        except:
            pass
    clients.clear()
    update_client_list()
    status_label.config(text="Server stopped", fg="red")
    log_output("[Server stopped]")
    start_btn.config(state="normal")
    stop_btn.config(state="disabled")

def update_client_list():
    client_list.delete(0, tk.END)
    for conn, (ip, port) in clients.items():
        client_list.insert(tk.END, f"{ip}:{port}")

def disconnect_selected_client():
    try:
        selection = client_list.curselection()
        if not selection:
            return
        index = selection[0]
        conn = list(clients.keys())[index]
        conn.send(b"exit")
        conn.close()
        log_output(f"[Manually disconnected] {clients[conn][0]}:{clients[conn][1]}")
    except Exception as e:
        messagebox.showerror("Error", str(e))

def clear_logs():
    log_box.config(state="normal")
    log_box.delete("1.0", tk.END)
    log_box.config(state="disabled")

# --- GUI ---
root = tk.Tk()
root.title("Ultimate Remote Server")
root.geometry("700x500")

# Top frame: port, access code, start/stop
frame_top = tk.Frame(root)
frame_top.pack(pady=5, fill="x")

tk.Label(frame_top, text="Port:").grid(row=0, column=0)
port_entry = tk.Entry(frame_top, width=6)
port_entry.insert(0, "9999")
port_entry.grid(row=0, column=1, padx=5)

tk.Label(frame_top, text="Access Code:").grid(row=0, column=2)
code_entry = tk.Entry(frame_top, width=12)
code_entry.insert(0, "1234")
code_entry.grid(row=0, column=3, padx=5)

start_btn = tk.Button(frame_top, text="Start Server", command=lambda: threading.Thread(target=start_server, daemon=True).start())
start_btn.grid(row=0, column=4, padx=5)

stop_btn = tk.Button(frame_top, text="Stop Server", command=stop_server, state="disabled")
stop_btn.grid(row=0, column=5, padx=5)

status_label = tk.Label(root, text="Stopped", fg="red")
status_label.pack()

# Middle frame: clients + logs
frame_middle = tk.Frame(root)
frame_middle.pack(fill="both", expand=True, padx=10)

client_frame = tk.Frame(frame_middle)
client_frame.pack(side="left", fill="y", padx=5)

tk.Label(client_frame, text="Connected Clients").pack()
client_list = tk.Listbox(client_frame, width=25)
client_list.pack(fill="y", expand=True)
disconnect_client_btn = tk.Button(client_frame, text="Disconnect Selected", command=disconnect_selected_client)
disconnect_client_btn.pack(pady=5)

log_frame = tk.Frame(frame_middle)
log_frame.pack(side="right", fill="both", expand=True)

tk.Label(log_frame, text="Command Logs").pack()
log_box = scrolledtext.ScrolledText(log_frame, state="disabled")
log_box.pack(fill="both", expand=True)

# Bottom frame: controls
frame_bottom = tk.Frame(root)
frame_bottom.pack(pady=5, fill="x")

auto_scroll_var = tk.BooleanVar(value=True)
tk.Checkbutton(frame_bottom, text="Auto-scroll", variable=auto_scroll_var).pack(side="left", padx=5)

theme_var = tk.StringVar(value="Light")
tk.OptionMenu(frame_bottom, theme_var, "Light", "Dark", command=lambda _: toggle_theme()).pack(side="left", padx=5)

tk.Button(frame_bottom, text="Clear Logs", command=clear_logs).pack(side="right", padx=5)

root.mainloop()
