#!/usr/bin/env python3
"""
Windows 11 Storage Monitor Client (GUI Python Version)
Interfaccia grafica Desktop in Python (Tkinter) per inviare lo stato storage al server.
"""

import sys
import os
import platform
import socket
import json
import urllib.request
import urllib.error
import time
import threading
import shutil
import tkinter as tk
from tkinter import ttk, messagebox

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"

def get_windows_drives():
    drives_list = []
    if platform.system() == "Windows":
        import ctypes
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            if bitmask & 1:
                drive_path = f"{letter}:\\"
                try:
                    usage = shutil.disk_usage(drive_path)
                    total_gb = round(usage.total / (1024**3), 2)
                    used_gb = round(usage.used / (1024**3), 2)
                    free_gb = round(usage.free / (1024**3), 2)
                    pct_used = round((usage.used / usage.total) * 100, 1) if usage.total > 0 else 0

                    drives_list.append({
                        "drive": f"{letter}:",
                        "label": "Disco Locale",
                        "total_gb": total_gb,
                        "used_gb": used_gb,
                        "free_gb": free_gb,
                        "percent_used": pct_used
                    })
                except Exception:
                    pass
            bitmask >>= 1
    else:
        # Fallback per test su Linux/macOS
        try:
            usage = shutil.disk_usage("/")
            total_gb = round(usage.total / (1024**3), 2)
            used_gb = round(usage.used / (1024**3), 2)
            free_gb = round(usage.free / (1024**3), 2)
            pct_used = round((usage.used / usage.total) * 100, 1)

            drives_list.append({
                "drive": "C:",
                "label": "Disco Sistema",
                "total_gb": total_gb,
                "used_gb": used_gb,
                "free_gb": free_gb,
                "percent_used": pct_used
            })
        except Exception:
            pass

    return drives_list

class StorageClientApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Windows 11 Storage Monitor Client")
        self.geometry("520x480")
        self.resizable(False, False)
        self.configure(bg="#0f172a")

        self.running = False
        self.interval = 10

        self._build_ui()

    def _build_ui(self):
        # Header Style
        title_label = tk.Label(self, text="💻 Windows Storage Monitor Client", font=("Segoe UI", 14, "bold"), fg="#f8fafc", bg="#0f172a")
        title_label.pack(pady=(15, 5))

        sub_label = tk.Label(self, text="Invia dati di storage e IP al Server centrale", font=("Segoe UI", 9), fg="#94a3b8", bg="#0f172a")
        sub_label.pack(pady=(0, 15))

        # Config Frame
        config_frame = tk.LabelFrame(self, text=" Impostazioni Server ", font=("Segoe UI", 9, "bold"), fg="#818cf8", bg="#1e293b", bd=1, relief="solid")
        config_frame.pack(fill="x", padx=20, pady=5)

        tk.Label(config_frame, text="URL Server:", font=("Segoe UI", 9), fg="#f8fafc", bg="#1e293b").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.url_entry = tk.Entry(config_frame, font=("Segoe UI", 10), width=28, bg="#0f172a", fg="#ffffff", insertbackground="white", bd=1)
        self.url_entry.insert(0, "http://localhost:8080")
        self.url_entry.grid(row=0, column=1, padx=5, pady=10)

        # Status & IP Frame
        info_frame = tk.Frame(self, bg="#0f172a")
        info_frame.pack(fill="x", padx=20, pady=10)

        self.ip_label = tk.Label(info_frame, text=f"IP Locale: {get_local_ip()}", font=("Consolas", 10, "bold"), fg="#10b981", bg="#0f172a")
        self.ip_label.pack(side="left")

        self.status_label = tk.Label(info_frame, text="Stato: Inattivo", font=("Segoe UI", 9), fg="#94a3b8", bg="#0f172a")
        self.status_label.pack(side="right")

        # Drives Treeview
        tree_frame = tk.Frame(self, bg="#0f172a")
        tree_frame.pack(fill="both", expand=True, padx=20, pady=5)

        columns = ("drive", "total", "used", "free", "pct")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=5)
        self.tree.heading("drive", text="Unità")
        self.tree.heading("total", text="Totale (GB)")
        self.tree.heading("used", text="Usato (GB)")
        self.tree.heading("free", text="Libero (GB)")
        self.tree.heading("pct", text="Uso %")

        self.tree.column("drive", width=60, anchor="center")
        self.tree.column("total", width=90, anchor="e")
        self.tree.column("used", width=90, anchor="e")
        self.tree.column("free", width=90, anchor="e")
        self.tree.column("pct", width=70, anchor="center")

        self.tree.pack(fill="both", expand=True)

        # Buttons
        btn_frame = tk.Frame(self, bg="#0f172a")
        btn_frame.pack(fill="x", padx=20, pady=15)

        self.toggle_btn = tk.Button(btn_frame, text="▶ Avvia Monitoraggio", font=("Segoe UI", 10, "bold"), bg="#6366f1", fg="white", activebackground="#4f46e5", activeforeground="white", bd=0, padx=15, pady=8, command=self.toggle_monitoring)
        self.toggle_btn.pack(side="left")

        send_now_btn = tk.Button(btn_frame, text="⚡ Invia Ora", font=("Segoe UI", 9), bg="#334155", fg="white", activebackground="#475569", activeforeground="white", bd=0, padx=12, pady=8, command=self.send_report_once)
        send_now_btn.pack(side="right")

        self.refresh_local_drives()

    def refresh_local_drives(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        drives = get_windows_drives()
        for d in drives:
            self.tree.insert("", "end", values=(d['drive'], d['total_gb'], d['used_gb'], d['free_gb'], f"{d['percent_used']}%"))

    def send_report(self):
        server_url = self.url_entry.get().strip().rstrip("/")
        report_url = f"{server_url}/api/report"

        drives = get_windows_drives()
        hostname = socket.gethostname()
        local_ip = get_local_ip()
        os_name = f"{platform.system()} {platform.release()}"

        payload = {
            "hostname": hostname,
            "ip": local_ip,
            "os": os_name,
            "drives": drives
        }

        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(report_url, data=data, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    return True, "Inviato con successo"
        except Exception as e:
            return False, str(e)
        return False, "Errore sconosciuto"

    def send_report_once(self):
        self.refresh_local_drives()
        success, msg = self.send_report()
        if success:
            messagebox.showinfo("Successo", "Report inviato al server con successo!")
        else:
            messagebox.showerror("Errore", f"Impossibile inviare il report:\n{msg}")

    def toggle_monitoring(self):
        if not self.running:
            self.running = True
            self.toggle_btn.config(text="⏹ Ferma Monitoraggio", bg="#ef4444", activebackground="#dc2626")
            self.status_label.config(text="Stato: Attivo 🟢", fg="#10b981")
            self.url_entry.config(state="disabled")
            threading.Thread(target=self._loop_worker, daemon=True).start()
        else:
            self.running = False
            self.toggle_btn.config(text="▶ Avvia Monitoraggio", bg="#6366f1", activebackground="#4f46e5")
            self.status_label.config(text="Stato: Inattivo", fg="#94a3b8")
            self.url_entry.config(state="normal")

    def _loop_worker(self):
        while self.running:
            success, msg = self.send_report()
            if success:
                self.after(0, lambda: self.status_label.config(text="Stato: Sincronizzato 🟢", fg="#10b981"))
                self.after(0, self.refresh_local_drives)
            else:
                self.after(0, lambda: self.status_label.config(text="Errore connessione 🔴", fg="#ef4444"))
            time.sleep(self.interval)

if __name__ == "__main__":
    app = StorageClientApp()
    app.mainloop()
