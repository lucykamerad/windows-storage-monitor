# 💻 Windows 11 Storage Monitor (Server & Client Static)

Una soluzione completa per monitorare in tempo reale l'utilizzo dello spazio su disco (storage) e l'indirizzo IP dei dispositivi Windows 11 su una dashboard web centrale con **avvio automatico al boot**.

---

## 🚀 1. Avvio del Server

Il server usa solo la libreria standard di Python 3 (nessuna dipendenza esterna).

```bash
python3 server.py        # porta 8080 di default
python3 server.py 9000   # porta personalizzata
```

- **Dashboard Web**: [http://localhost:8080](http://localhost:8080).
- **Autostart (Linux)**: puoi eseguirlo come servizio `systemd`.

### ⚠️ Nessuna autenticazione

La dashboard e le API **non hanno login**: chiunque raggiunga la porta del server può vedere i dati dei client e rimuoverli dalla lista. Usalo solo su una rete fidata (LAN), dietro firewall/VPN, oppure metti davanti un reverse proxy con autenticazione. Non esporlo direttamente su internet.

### Indirizzo del server nei client

Nessun IP è scritto nel codice. Ogni installer chiede l'indirizzo del server (es. `http://192.168.1.100:8080`) e lo salva in `%LOCALAPPDATA%\WindowsStorageMonitor\server_url.txt`. Il client C# cerca l'indirizzo in quest'ordine: argomento da riga di comando, variabile `STORAGE_MONITOR_URL`, `server_url.txt` accanto all'exe, il file in `%LOCALAPPDATA%`, infine `http://localhost:8080`.

---

## 📦 2. Pacchetto di Produzione per Windows 11 (`CLIENT_PRODUCTION_PACKAGE`)

È stata creata la cartella **`CLIENT_PRODUCTION_PACKAGE`** pronta da inviare o distribuire sui PC Windows 11.

Per installare un client in produzione (1 Click):
1. Copia la cartella `CLIENT_PRODUCTION_PACKAGE` su qualsiasi PC Windows 11.
2. Fai doppio-click su **`INSTALLA_PRODUZIONE.bat`**.

### ✨ Cosa fa l'installatore in automatico:
- Compila l'eseguibile nativo totalmente **invisibile** in background (`StorageMonitorClient.exe`).
- Lo aggiunge all'**Avvio Automatico di Windows** (`Startup`).
- Lo avvia immediatamente.
- **Monitora in tempo reale**:
  - 💾 Tutti i **Dischi Fissi** (C:, D:, ecc.)
  - 🧹 **Temp Utente** (`%TEMP%`)
  - 🧹 **Temp di Sistema** (`C:\Windows\Temp`)
  - 🗑️ **Cestino di Windows** (`C:\$Recycle.Bin`)
  - 📦 **Cache Windows Update** (`C:\Windows\SoftwareDistribution\Download`)
  - 📜 **File di Log di Sistema** (`C:\Windows\Logs`)

---

## 🗑️ Disinstallazione Client
Per rimuovere il client da un PC Windows 11, fai doppio-click su `DISINSTALLA_CLIENT.bat`.
