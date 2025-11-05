<div align="left">

# Python Remote Control Connector

This Python setup lets you **run commands on another PC**.  

- **Server**: Runs on the PC you want to control.  
- **Client**: Runs on the PC you use to control the server.  

---

## 1️⃣ Using LAN (Local Network)

- Both PCs must be on the **same network** (Wi-Fi or Ethernet).  
- Find the server PC’s **local IP**:  
  - Open Command Prompt and type: `ipconfig` → look for **IPv4 Address**.  
- Use this IP in the client to connect.  
- **No router changes needed.**  
- Fast and simple.  

---

## 2️⃣ Using Internet (Remote Access)

- Allows control across **different networks**.  
- Steps:  
  1. Find the server PC’s **public IP**.  
  2. Set up **port forwarding** on port `9999`.  
  3. Allow Python through **Windows Firewall**.  
  4. Optional: Use a **VPN** for safer access.  

# Auto
> Use Same Client  
> for Auto run:

`pip install pillow pystray`

</div>
