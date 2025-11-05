# Python Remote Control Connector

Control another PC with Python. Simple setup, powerful results.  

- **Server** → The PC you want to control.  
- **Client** → The PC you control from.  

---

## 1️⃣ LAN Mode (Local Network)

- Both PCs need to be on the **same network** (Wi-Fi or Ethernet).  
- Find the server PC’s **local IP**:  
  - Open Command Prompt → type `ipconfig` → look for **IPv4 Address**.  
- Enter that IP in the client to connect.  
- **No router setup needed.**  
- Super fast and easy.  

---

## 2️⃣ Internet Mode (Remote Access)

Control your PC from anywhere. Steps:  

1. Find the server PC’s **public IP**.  
2. Set up **port forwarding** for port `9999` on your router.  
3. Allow Python through **Windows Firewall**.  
4. Optional: Use a **VPN** for extra security.  

---

## ⚡ Auto-Start Setup

Make your server launch automatically:  

1. Open the Auto-Server config (lines 24–29) and set your values:

    ```
    # ---------------- Auto-Start Configuration ----------------
    BIND_IP = "192.168.1.124"
    BIND_PORT = 2357
    ACCESS_CODE = "2357"
    ```

2. Install dependencies if missing:

    ```
    pip install pystray pillow
    ```

3. (Optional) Create a shortcut and place it in `shell:startup` to run on boot.
