#!/usr/bin/env python3
"""Windows Storage Monitor - Server"""

import http.server
import socketserver
import json
import socket
import urllib.parse
import sys
from datetime import datetime
import threading

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MAX_BODY_BYTES       = 512 * 1024   # max POST size for client reports
HOSTNAME_MAX_LEN     = 64

# Report limits
MAX_DRIVES_PER_REPORT = 26
MAX_BLOAT_PER_REPORT  = 50
MAX_FIELD_LEN         = 256

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------
CLIENTS_DATA = {}   # hostname -> data dict
DATA_LOCK    = threading.Lock()


# ---------------------------------------------------------------------------
# Security helpers
# ---------------------------------------------------------------------------
def sanitize_hostname(raw):
    safe = raw[:HOSTNAME_MAX_LEN]
    safe = ''.join(c for c in safe if c.isalnum() or c in '-_.')
    return safe or 'Client-Unknown'

def sanitize_str(raw, maxlen=MAX_FIELD_LEN):
    """Truncate and strip a string field from untrusted input."""
    return str(raw)[:maxlen]

def validate_drive(d):
    """Return True if a drive dict has the expected numeric/string fields."""
    if not isinstance(d, dict):
        return False
    for key in ('used_gb', 'total_gb', 'free_gb', 'percent_used'):
        if key in d:
            try:
                float(d[key])
            except (TypeError, ValueError):
                return False
    return True

def validate_bloat(b):
    """Return True if a bloat dict has the expected fields."""
    return isinstance(b, dict)

def get_server_ips():
    ips = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and ip not in ips:
            ips.insert(0, ip)
    except Exception:
        pass
    try:
        for addr in socket.getaddrinfo(socket.gethostname(), None):
            ip = addr[4][0]
            if ':' not in ip and not ip.startswith('127.') and ip not in ips:
                ips.append(ip)
    except Exception:
        pass
    return ips or ['127.0.0.1']

def _log(msg):
    sys.stdout.write(f'[{datetime.now().strftime("%H:%M:%S")}] {msg}\n')
    sys.stdout.flush()


DASHBOARD_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Storage Monitor</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            font-size: 14px;
            background: #111418;
            color: #d4d9e0;
            min-height: 100vh;
        }
        .topbar {
            background: #1a1e24;
            border-bottom: 1px solid #2a2f38;
            padding: 0 1.25rem;
            height: 44px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
        }
        .topbar-title {
            font-size: 0.82rem;
            font-weight: 600;
            color: #b0bec8;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }
        .main { max-width: 1400px; margin: 0 auto; padding: 1.1rem 1.25rem; }
        .stats-bar {
            display: flex;
            gap: 1px;
            background: #2a2f38;
            border: 1px solid #2a2f38;
            border-radius: 3px;
            overflow: hidden;
            margin-bottom: 1rem;
        }
        .stat-block { flex: 1; background: #1a1e24; padding: 0.75rem 1rem; }
        .stat-label {
            font-size: 0.67rem;
            text-transform: uppercase;
            letter-spacing: 0.07em;
            color: #4a5568;
            margin-bottom: 0.2rem;
        }
        .stat-value {
            font-size: 1.35rem;
            font-weight: 700;
            color: #c8d4e0;
            font-variant-numeric: tabular-nums;
        }
        .stat-sub { font-size: 0.68rem; color: #c0392b; margin-top: 0.1rem; font-weight: 600; }
        .controls {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 0.85rem;
            flex-wrap: wrap;
        }
        .controls input[type=text] {
            padding: 0.4rem 0.65rem;
            background: #1a1e24;
            border: 1px solid #2a2f38;
            border-radius: 2px;
            color: #d4d9e0;
            font-size: 0.82rem;
            outline: none;
            width: 220px;
            font-family: inherit;
        }
        .controls input[type=text]:focus { border-color: #4a90d9; }
        .controls select {
            padding: 0.4rem 0.6rem;
            background: #1a1e24;
            border: 1px solid #2a2f38;
            border-radius: 2px;
            color: #d4d9e0;
            font-size: 0.82rem;
            outline: none;
            cursor: pointer;
            font-family: inherit;
        }
        .controls select:focus { border-color: #4a90d9; }
        .btn-ctrl {
            padding: 0.4rem 0.75rem;
            background: #1a1e24;
            border: 1px solid #2a2f38;
            border-radius: 2px;
            color: #6b7785;
            font-size: 0.78rem;
            cursor: pointer;
            font-family: inherit;
            transition: background 0.15s, color 0.15s;
        }
        .btn-ctrl:hover { background: #222a35; color: #c8d4e0; }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
            gap: 1px;
            background: #2a2f38;
            border: 1px solid #2a2f38;
            border-radius: 3px;
            overflow: hidden;
        }
        .card { background: #1a1e24; padding: 0.9rem 1rem; position: relative; }
        .card.offline { background: #161a1e; }
        .card-head {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 0.65rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid #1e232a;
        }
        .card-left { display: flex; flex-direction: column; gap: 0.15rem; }
        .card-hostname {
            font-size: 0.9rem;
            font-weight: 700;
            color: #c8d4e0;
            font-family: "Consolas", "Courier New", monospace;
        }
        .card-hostname.dim { color: #3d4a58; }
        .card-os   { font-size: 0.68rem; color: #4a5568; }
        .card-user { font-size: 0.72rem; color: #4a90d9; font-family: "Consolas", monospace; }
        .card-offline-tag {
            font-size: 0.62rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #3d4a58;
            border: 1px solid #252c37;
            padding: 0.1rem 0.35rem;
            border-radius: 2px;
        }
        .card-ip {
            font-family: "Consolas", "Courier New", monospace;
            font-size: 0.78rem;
            color: #4a90d9;
            text-align: right;
        }
        .card-ip.dim { color: #2a3040; }
        .sec-label {
            font-size: 0.64rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #333d4a;
            margin: 0.65rem 0 0.35rem;
            padding-bottom: 0.2rem;
            border-bottom: 1px solid #1c2028;
        }
        .drive-row { margin-bottom: 0.45rem; }
        .drive-row:last-child { margin-bottom: 0; }
        .drive-info {
            display: flex;
            justify-content: space-between;
            font-size: 0.74rem;
            color: #6b7785;
            margin-bottom: 0.18rem;
            font-family: "Consolas", "Courier New", monospace;
        }
        .drive-id { color: #8899aa; font-weight: 600; }
        .bar-bg { height: 4px; background: #1e232a; border-radius: 2px; overflow: hidden; }
        .bar-fill { height: 100%; border-radius: 2px; transition: width 0.4s ease; }
        .bar-ok   { background: #27ae60; }
        .bar-warn { background: #d35400; }
        .bar-crit { background: #c0392b; }
        .bloat-row {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            padding: 0.18rem 0;
            border-bottom: 1px solid #1c2028;
            font-size: 0.74rem;
        }
        .bloat-row:last-child { border-bottom: none; }
        .bloat-left { display: flex; flex-direction: column; }
        .bloat-name { color: #8899aa; }
        .bloat-path {
            font-family: "Consolas", monospace;
            font-size: 0.63rem;
            color: #333d4a;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            max-width: 240px;
        }
        .bloat-size {
            font-family: "Consolas", monospace;
            font-size: 0.74rem;
            font-weight: 600;
            white-space: nowrap;
            margin-left: 0.5rem;
        }
        .sz-ok   { color: #27ae60; }
        .sz-warn { color: #d35400; }
        .sz-crit { color: #c0392b; }
        .no-data { font-size: 0.7rem; color: #333d4a; font-style: italic; }
        .card-foot {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 0.65rem;
            padding-top: 0.45rem;
            border-top: 1px solid #1c2028;
            font-size: 0.68rem;
            color: #333d4a;
            font-family: "Consolas", monospace;
        }
        .btn-del {
            background: none;
            border: none;
            color: #333d4a;
            cursor: pointer;
            font-size: 0.72rem;
            padding: 0.1rem 0.3rem;
            font-family: inherit;
            transition: color 0.15s;
        }
        .btn-del:hover { color: #c0392b; }
        .empty {
            grid-column: 1 / -1;
            padding: 2.5rem;
            text-align: center;
            color: #333d4a;
            font-size: 0.82rem;
            background: #1a1e24;
        }
        #toast {
            position: fixed; bottom: 1rem; right: 1rem;
            background: #1a1e24; border: 1px solid #2a2f38;
            color: #8899aa; padding: 0.5rem 0.9rem;
            border-radius: 2px; font-size: 0.78rem;
            font-family: "Consolas", monospace;
            opacity: 0; pointer-events: none;
            transition: opacity 0.2s; z-index: 200;
        }
        #toast.show { opacity: 1; }
    </style>
</head>
<body>

<div class="topbar">
    <span class="topbar-title">Storage Monitor</span>
</div>

<div class="main">
    <div class="stats-bar">
        <div class="stat-block">
            <div class="stat-label">Hosts</div>
            <div class="stat-value" id="stat-pcs">0</div>
            <div class="stat-sub" id="stat-offline-sub"></div>
        </div>
        <div class="stat-block">
            <div class="stat-label">Drives</div>
            <div class="stat-value" id="stat-drives">0</div>
        </div>
        <div class="stat-block">
            <div class="stat-label">Total Space</div>
            <div class="stat-value" id="stat-space">--</div>
        </div>
        <div class="stat-block">
            <div class="stat-label">Temp / Cache</div>
            <div class="stat-value" id="stat-bloat">--</div>
        </div>
        <div class="stat-block">
            <div class="stat-label">Last Refresh</div>
            <div class="stat-value" style="font-size:0.9rem;padding-top:0.3rem" id="stat-ts">--</div>
        </div>
    </div>

    <div class="controls">
        <input type="text" id="search-input" placeholder="Filter hostname / IP / user..." oninput="onFilter()">
        <select id="sort-select" onchange="onSort()">
            <option value="hostname">Sort: Hostname</option>
            <option value="ip">Sort: IP</option>
            <option value="space_used">Sort: Space used</option>
            <option value="last_update">Sort: Last seen</option>
        </select>
        <button class="btn-ctrl" id="btn-refresh">Refresh</button>
    </div>

    <div class="grid" id="clients-grid"></div>
</div>

<div id="toast"></div>

<script>
    /* ---- Constants ---- */
    const OFFLINE_MS   = 90000;

    let allClients = {};

    /* ---- Safe HTML escape ---- */
    function escHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#x27;');
    }

    /* ---- Per-user UI state in localStorage ---- */
    function loadUIState() {
        try {
            const s = JSON.parse(localStorage.getItem('sm_ui') || '{}');
            if (s.filter) document.getElementById('search-input').value = s.filter;
            if (s.sort)   document.getElementById('sort-select').value   = s.sort;
        } catch (e) {}
    }
    function saveUIState() {
        try {
            localStorage.setItem('sm_ui', JSON.stringify({
                filter: document.getElementById('search-input').value,
                sort:   document.getElementById('sort-select').value,
            }));
        } catch (e) {}
    }
    function onFilter() { saveUIState(); renderClients(); }
    function onSort()   { saveUIState(); renderClients(); }

    /* ---- Formatting ---- */
    function fmtMB(mb) {
        if (mb <= 0)    return '0 MB';
        if (mb < 1)     return '< 1 MB';
        if (mb >= 1024) return (mb / 1024).toFixed(2) + ' GB';
        return mb.toFixed(1) + ' MB';
    }
    function fmtGB(gb) {
        if (gb >= 1024) return (gb / 1024).toFixed(2) + ' TB';
        return gb.toFixed(1) + ' GB';
    }

    /* ---- Misc ---- */
    function showToast(msg) {
        const t = document.getElementById('toast');
        t.textContent = msg;
        t.classList.add('show');
        setTimeout(() => t.classList.remove('show'), 2500);
    }
    function isOffline(c) {
        if (!c.last_update) return true;
        return (Date.now() - new Date(c.last_update).getTime()) > OFFLINE_MS;
    }
    function totalUsedGB(c) {
        return (c.drives || []).reduce((s, d) => s + (parseFloat(d.used_gb) || 0), 0);
    }
    function totalBloatMB(c) {
        return (c.bloat_folders || []).reduce((s, b) => s + (parseFloat(b.size_mb) || 0), 0);
    }

    /* ---- Data fetch ---- */
    async function fetchClients() {
        try {
            const res = await fetch('/api/clients', {credentials: 'same-origin'});
            if (!res.ok) throw new Error('HTTP ' + res.status);
            allClients = await res.json();
            renderClients();
            document.getElementById('stat-ts').textContent =
                new Date().toLocaleTimeString('it-IT');
        } catch (err) {
            showToast('Connection error');
        }
    }

    /* ---- Render ---- */
    function renderClients() {
        const grid   = document.getElementById('clients-grid');
        const search = document.getElementById('search-input').value.toLowerCase().trim();
        const sort   = document.getElementById('sort-select').value;

        let keys = Object.keys(allClients);
        if (search) {
            keys = keys.filter(k => {
                const c = allClients[k];
                return k.toLowerCase().includes(search)
                    || (c.ip       || '').toLowerCase().includes(search)
                    || (c.username || '').toLowerCase().includes(search);
            });
        }
        keys.sort((a, b) => {
            const ca = allClients[a], cb = allClients[b];
            if (sort === 'ip')          return (ca.ip || '').localeCompare(cb.ip || '');
            if (sort === 'space_used')  return totalUsedGB(cb) - totalUsedGB(ca);
            if (sort === 'last_update') return new Date(cb.last_update) - new Date(ca.last_update);
            return a.localeCompare(b);
        });

        const all = Object.values(allClients);
        let td = 0, ts = 0, tb = 0, off = 0;
        all.forEach(c => {
            if (isOffline(c)) off++;
            (c.drives || []).forEach(d => { td++; ts += parseFloat(d.total_gb) || 0; });
            tb += totalBloatMB(c);
        });
        document.getElementById('stat-pcs').textContent    = all.length;
        document.getElementById('stat-drives').textContent = td;
        document.getElementById('stat-space').textContent  = all.length ? fmtGB(ts) : '--';
        document.getElementById('stat-bloat').textContent  = all.length ? fmtMB(tb) : '--';
        document.getElementById('stat-offline-sub').textContent =
            off > 0 ? off + ' offline' : '';

        if (keys.length === 0) {
            grid.innerHTML = '<div class="empty">'
                + (search ? 'No results.' : 'No clients connected.') + '</div>';
            return;
        }
        grid.innerHTML = keys.map(h => buildCard(h, allClients[h])).join('');
    }

    /* ---- Card builder: NO inline JS in event handlers ----
       All user data goes into data-* attributes (HTML-escaped),
       then read back via dataset in the event delegation handler.
       This prevents XSS even if escHtml were bypassed. */
    function buildCard(hostname, c) {
        const offline  = isOffline(c);
        const lastDate = new Date(c.last_update);
        const lastFmt  = isNaN(lastDate.getTime()) ? 'N/D'
            : lastDate.toLocaleString('it-IT', {dateStyle:'short', timeStyle:'medium'});

        const drives = (c.drives || []).map(d => {
            const pct = Math.min(100, Math.max(0, parseFloat(d.percent_used) || 0));
            const cls = pct >= 90 ? 'bar-crit' : pct >= 70 ? 'bar-warn' : 'bar-ok';
            return '<div class="drive-row">'
                + '<div class="drive-info">'
                + '<span class="drive-id">' + escHtml(d.drive || '')
                + (d.label ? ' [' + escHtml(d.label) + ']' : '') + '</span>'
                + '<span>' + (parseFloat(d.used_gb)||0).toFixed(1) + ' / '
                + (parseFloat(d.total_gb)||0).toFixed(1) + ' GB &mdash; '
                + pct.toFixed(1) + '%</span></div>'
                + '<div class="bar-bg"><div class="bar-fill ' + cls
                + '" style="width:' + pct + '%"></div></div></div>';
        }).join('') || '<div class="no-data">No drives.</div>';

        const bloatFolders = c.bloat_folders || [];
        const bloat = bloatFolders.length === 0
            ? '<div class="no-data">No data.</div>'
            : bloatFolders.map(b => {
                const mb  = parseFloat(b.size_mb) || 0;
                const cls = mb > 5000 ? 'sz-crit' : mb > 1000 ? 'sz-warn' : 'sz-ok';
                return '<div class="bloat-row"><div class="bloat-left">'
                    + '<span class="bloat-name">' + escHtml(b.name  || '') + '</span>'
                    + '<span class="bloat-path">' + escHtml(b.path  || '') + '</span></div>'
                    + '<span class="bloat-size ' + cls + '">' + fmtMB(mb) + '</span></div>';
            }).join('');

        /* data-hostname stores the HTML-escaped value; dataset.hostname gives back the
           decoded string safely — no JS string injection possible */
        return '<div class="card' + (offline ? ' offline' : '') + '">'
            + '<div class="card-head">'
            + '<div class="card-left">'
            + '<div class="card-hostname' + (offline ? ' dim' : '') + '">' + escHtml(hostname) + '</div>'
            + '<div class="card-os">'   + escHtml(c.os || 'Windows') + '</div>'
            + (c.username ? '<div class="card-user">' + escHtml(c.username) + '</div>' : '')
            + (offline ? '<span class="card-offline-tag">offline</span>' : '')
            + '</div>'
            + '<div class="card-ip' + (offline ? ' dim' : '') + '">' + escHtml(c.ip || 'N/D') + '</div>'
            + '</div>'
            + '<div class="sec-label">Drives</div>'  + drives
            + '<div class="sec-label">Temp / Cache</div>' + bloat
            + '<div class="card-foot">'
            + '<span>last seen: ' + escHtml(lastFmt) + '</span>'
            + '<button class="btn-del" data-action="rm-client"'
            + ' data-hostname="' + escHtml(hostname) + '">[remove]</button>'
            + '</div></div>';
    }

    /* ---- Event delegation (no inline onclick with user data) ---- */
    document.getElementById('clients-grid').addEventListener('click', function(e) {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;
        if (btn.dataset.action === 'rm-client') removeClient(btn.dataset.hostname);
    });

    async function removeClient(hostname) {
        if (!confirm('Remove "' + hostname + '" from dashboard?')) return;
        try {
            const res = await fetch('/api/clients/' + encodeURIComponent(hostname),
                {method: 'DELETE', credentials: 'same-origin'});
            if (res.ok) {
                delete allClients[hostname];
                renderClients();
                showToast('Removed: ' + hostname);
            } else {
                showToast('Error removing client.');
            }
        } catch (e) {
            showToast('Network error.');
        }
    }

    /* ---- Wire up static buttons (no inline onclick needed) ---- */
    document.getElementById('btn-refresh').addEventListener('click', fetchClients);

    /* ---- Boot ---- */
    loadUIState();
    fetchClients();
    setInterval(fetchClients, 10000);
</script>
</body>
</html>"""


# Security headers sent on every HTML/JSON response
_SEC_HEADERS = [
    ('X-Content-Type-Options',  'nosniff'),
    ('X-Frame-Options',         'DENY'),
    ('Referrer-Policy',         'same-origin'),
    # CSP: only same-origin resources; unsafe-inline needed for our inline script/style
    ('Content-Security-Policy',
     "default-src 'self'; script-src 'self' 'unsafe-inline'; "
     "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
     "connect-src 'self'; object-src 'none'; frame-ancestors 'none'"),
]


# ---------------------------------------------------------------------------
# HTTP Handler
# ---------------------------------------------------------------------------
class StorageMonitorHTTPHandler(http.server.BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        _log(f'{self.client_address[0]} - {fmt % args}')

    # --- Response helpers ---
    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        for k, v in _SEC_HEADERS:
            self.send_header(k, v)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html, status=200):
        body = html.encode('utf-8')
        self.send_response(status)
        for k, v in _SEC_HEADERS:
            self.send_header(k, v)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # --- Safe body reader ---
    def _read_body(self, max_bytes):
        """Read up to max_bytes from request body. Returns bytes or None on error."""
        try:
            length = int(self.headers.get('Content-Length', 0))
        except (ValueError, TypeError):
            return None
        if length < 0 or length > max_bytes:
            return None
        return self.rfile.read(length)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path

        if path in ('/', '/index.html'):
            self._send_html(DASHBOARD_TEMPLATE)

        elif path == '/api/clients':
            with DATA_LOCK:
                self._send_json(dict(CLIENTS_DATA))

        else:
            self.send_error(404, 'Not found')

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        client_ip = self.client_address[0]

        # ---- Client report ----
        if path == '/api/report':
            try:
                body = self._read_body(MAX_BODY_BYTES)
                if body is None:
                    self._send_json({'status': 'error', 'message': 'Payload too large or missing Content-Length'}, 413)
                    return

                payload = json.loads(body.decode('utf-8'))
                if not isinstance(payload, dict):
                    raise ValueError('Payload must be a JSON object')

                hostname  = sanitize_hostname(str(payload.get('hostname', '')).strip())
                client_ip_reported = sanitize_str(str(payload.get('ip') or client_ip))
                os_name   = sanitize_str(str(payload.get('os', 'Windows')))
                username  = sanitize_str(str(payload.get('username', '')))

                raw_drives = payload.get('drives', [])
                raw_bloat  = payload.get('bloat_folders', [])

                if not isinstance(raw_drives, list): raw_drives = []
                if not isinstance(raw_bloat,  list): raw_bloat  = []

                # Validate and sanitize each drive entry
                drives = []
                for d in raw_drives[:MAX_DRIVES_PER_REPORT]:
                    if not validate_drive(d):
                        continue
                    drives.append({
                        'drive':       sanitize_str(str(d.get('drive',       ''))),
                        'label':       sanitize_str(str(d.get('label',       ''))),
                        'total_gb':    round(float(d.get('total_gb',    0)), 3),
                        'used_gb':     round(float(d.get('used_gb',     0)), 3),
                        'free_gb':     round(float(d.get('free_gb',     0)), 3),
                        'percent_used':round(float(d.get('percent_used',0)), 2),
                    })

                # Validate and sanitize each bloat entry
                bloat = []
                for b in raw_bloat[:MAX_BLOAT_PER_REPORT]:
                    if not validate_bloat(b):
                        continue
                    bloat.append({
                        'name':    sanitize_str(str(b.get('name',    ''))),
                        'path':    sanitize_str(str(b.get('path',    ''))),
                        'size_mb': round(float(b.get('size_mb', 0)), 3),
                    })

                with DATA_LOCK:
                    CLIENTS_DATA[hostname] = {
                        'hostname':      hostname,
                        'ip':            client_ip_reported,
                        'os':            os_name,
                        'username':      username,
                        'drives':        drives,
                        'bloat_folders': bloat,
                        'last_update':   datetime.now().isoformat(),
                    }

                _log(f'Report: {hostname} ({client_ip}, {username or "N/D"}) '
                     f'{len(drives)} drives {len(bloat)} bloat')
                self._send_json({'status': 'ok'})

            except (json.JSONDecodeError, ValueError) as e:
                _log(f'Report parse error from {client_ip}: {e}')
                self._send_json({'status': 'error', 'message': 'Invalid payload'}, 400)
            except Exception as e:
                _log(f'Report error: {e}')
                self._send_json({'status': 'error', 'message': 'Server error'}, 500)
            return

        self.send_error(404, 'Not found')

    def do_DELETE(self):
        path = urllib.parse.urlparse(self.path).path

        # ---- Remove client ----
        if path.startswith('/api/clients/'):
            hostname = sanitize_hostname(
                urllib.parse.unquote(path[len('/api/clients/'):]))
            with DATA_LOCK:
                if hostname in CLIENTS_DATA:
                    del CLIENTS_DATA[hostname]
                    self._send_json({'status': 'ok'})
                else:
                    self._send_json({'status': 'error', 'message': 'Client not found'}, 404)
            return

        self.send_error(404, 'Not found')


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads      = True


def run_server(port=8080):
    server = ThreadedHTTPServer(('', port), StorageMonitorHTTPHandler)
    ips    = get_server_ips()
    sep = '=' * 60
    print(sep)
    print(' WINDOWS STORAGE MONITOR')
    print(sep)
    print(f' Dashboard : http://localhost:{port}')
    print(' Network IPs:')
    for ip in ips:
        print(f'   http://{ip}:{port}')
    print(sep)
    print()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n[!] Shutting down...')
        server.shutdown()


if __name__ == '__main__':
    port = 8080
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    run_server(port)
