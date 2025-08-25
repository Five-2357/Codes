# server_gui_buttons.py
import socket
import threading
import subprocess
import tkinter as tk

PORT = 9999
ACCESS_CODE = "1234"  # unique per PC

def handle_client(conn, addr):
    conn.send(b"Enter access code: ")
    code = conn.recv(1024).decode().strip()
    if code != ACCESS_CODE:
        conn.send(b"Wrong code. Disconnecting.")
        conn.close()
        return
    conn.send(b"Access granted. Ready.\n")
    
    while True:
        try:
            cmd = conn.recv(4096).decode()
            if not cmd or cmd.lower() == "exit":
                break
            output = subprocess.getoutput(cmd)
            if not output:
                output = "[Command executed]"
            conn.send(output.encode())
        except:
            break
    conn.close()

def start_server():
    s = socket.socket()
    s.bind(("0.0.0.0", PORT))
    s.listen()
    status_label.config(text=f"Server listening on port {PORT}")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

# GUI
root = tk.Tk()
root.title("Remote Control Server")
root.geometry("400x150")

status_label = tk.Label(root, text="Server not running", fg="red")
status_label.pack(pady=20)

start_btn = tk.Button(root, text="Start Server", command=lambda: threading.Thread(target=start_server, daemon=True).start())
start_btn.pack()

root.mainloop()
