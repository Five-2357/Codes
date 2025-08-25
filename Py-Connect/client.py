# client_gui_full.py
import os, socket, threading, tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog

# Hide console on Windows
if os.name == "nt":
    try:
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except:
        pass

client_socket = None
connected = False
command_history = []
history_index = -1
auto_scroll = True

# ---------- FUNCTIONS ----------
def log_output(text):
    output_box.config(state="normal")
    output_box.insert(tk.END, text + "\n")
    if auto_scroll_var.get():
        output_box.see(tk.END)
    output_box.config(state="disabled")

def connect_to_server():
    global client_socket, connected
    ip = ip_entry.get().strip()
    port = int(port_entry.get().strip())
    code = code_entry.get().strip()
    try:
        client_socket = socket.socket()
        client_socket.settimeout(5)
        client_socket.connect((ip, port))

        prompt = client_socket.recv(1024).decode()
        log_output(prompt)

        client_socket.send(code.encode())
        response = client_socket.recv(1024).decode()
        log_output(response)

        if "Wrong" in response:
            client_socket.close()
            messagebox.showerror("Access Denied", "Wrong access code")
            status_label.config(text="Disconnected", fg="red")
            return

        connected = True
        connect_btn.config(state="disabled")
        disconnect_btn.config(state="normal")
        send_btn.config(state="normal")
        status_label.config(text="Connected", fg="green")
    except Exception as e:
        messagebox.showerror("Connection Error", str(e))
        status_label.config(text="Error", fg="orange")

def disconnect_from_server():
    global client_socket, connected
    try:
        if client_socket:
            client_socket.send(b"exit")
            client_socket.close()
    except:
        pass
    connected = False
    connect_btn.config(state="normal")
    disconnect_btn.config(state="disabled")
    send_btn.config(state="disabled")
    status_label.config(text="Disconnected", fg="red")
    log_output("[Disconnected]")

def send_command(event=None):
    global client_socket, command_history, history_index
    cmd = cmd_entry.get().strip()
    if not cmd or not connected:
        return
    try:
        client_socket.send(cmd.encode())
        output = client_socket.recv(4096).decode()
        log_output(f"> {cmd}\n{output}\n")
        command_history.append(cmd)
        history_index = len(command_history)
        cmd_entry.delete(0, tk.END)
    except Exception as e:
        messagebox.showerror("Command Error", str(e))
        disconnect_from_server()

def save_output():
    filename = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files","*.txt")])
    if filename:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(output_box.get("1.0", tk.END))
        messagebox.showinfo("Saved", f"Output saved to {filename}")

def clear_output():
    output_box.config(state="normal")
    output_box.delete("1.0", tk.END)
    output_box.config(state="disabled")

def recall_command(event):
    global command_history, history_index
    if not command_history:
        return
    if event.keysym == "Up":
        history_index = max(0, history_index - 1)
        cmd_entry.delete(0, tk.END)
        cmd_entry.insert(0, command_history[history_index])
    elif event.keysym == "Down":
        history_index = min(len(command_history)-1, history_index + 1)
        cmd_entry.delete(0, tk.END)
        cmd_entry.insert(0, command_history[history_index])

def toggle_theme():
    if theme_var.get() == "Dark":
        root.configure(bg="#222")
        output_box.configure(bg="#000", fg="#0f0")
    else:
        root.configure(bg="#eee")
        output_box.configure(bg="#fff", fg="#000")

# ---------- GUI ----------
root = tk.Tk()
root.title("Ultimate Remote Client")
root.geometry("650x500")

# Connection frame
frame_conn = tk.Frame(root)
frame_conn.pack(pady=5, fill="x")

tk.Label(frame_conn, text="IP:").grid(row=0, column=0)
ip_entry = tk.Entry(frame_conn, width=12)
ip_entry.insert(0, "127.0.0.1")
ip_entry.grid(row=0, column=1, padx=5)

tk.Label(frame_conn, text="Port:").grid(row=0, column=2)
port_entry = tk.Entry(frame_conn, width=6)
port_entry.insert(0, "9999")
port_entry.grid(row=0, column=3, padx=5)

tk.Label(frame_conn, text="Code:").grid(row=0, column=4)
code_entry = tk.Entry(frame_conn, width=10, show="*")
code_entry.insert(0, "1234")
code_entry.grid(row=0, column=5, padx=5)

connect_btn = tk.Button(frame_conn, text="Connect", command=connect_to_server)
connect_btn.grid(row=0, column=6, padx=5)
disconnect_btn = tk.Button(frame_conn, text="Disconnect", command=disconnect_from_server, state="disabled")
disconnect_btn.grid(row=0, column=7, padx=5)

# Status
status_label = tk.Label(root, text="Disconnected", fg="red")
status_label.pack()

# Command frame
frame_cmd = tk.Frame(root)
frame_cmd.pack(pady=5, fill="x")
cmd_entry = tk.Entry(frame_cmd)
cmd_entry.grid(row=0, column=0, padx=5, sticky="we")
cmd_entry.bind("<Up>", recall_command)
cmd_entry.bind("<Down>", recall_command)
send_btn = tk.Button(frame_cmd, text="Send", command=send_command, state="disabled")
send_btn.grid(row=0, column=1, padx=5)

# Output box
output_box = scrolledtext.ScrolledText(root, wrap=tk.WORD, state="disabled", height=20)
output_box.pack(fill="both", expand=True, padx=10, pady=10)

# Bottom controls
frame_bottom = tk.Frame(root)
frame_bottom.pack(pady=5, fill="x")

auto_scroll_var = tk.BooleanVar(value=True)
tk.Checkbutton(frame_bottom, text="Auto-scroll", variable=auto_scroll_var).pack(side="left", padx=5)

theme_var = tk.StringVar(value="Light")
tk.OptionMenu(frame_bottom, theme_var, "Light", "Dark", command=lambda _: toggle_theme()).pack(side="left", padx=5)

tk.Button(frame_bottom, text="Clear Output", command=clear_output).pack(side="right", padx=5)
tk.Button(frame_bottom, text="Save Output", command=save_output).pack(side="right", padx=5)

root.mainloop()
