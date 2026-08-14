"""
Embedded Mobile Web Remote Assets (HTML5, Vanilla CSS, JS) for MadGrav Laser Controller.
"""

def get_mobile_remote_html(csrf_token: str, device_name: str = "MadGrav Laser") -> str:
    """Returns the full single-page mobile web remote HTML string."""
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="theme-color" content="#12151c">
    <title>MadGrav Télécommande Laser</title>
    <style>
        :root {{
            --bg-main: #12151c;
            --bg-card: #1c212d;
            --bg-btn: #283042;
            --bg-btn-hover: #37425b;
            --accent: #2563eb;
            --accent-hover: #1d4ed8;
            --danger: #dc2626;
            --success: #16a34a;
            --warning: #eab308;
            --text: #f8fafc;
            --text-dim: #94a3b8;
            --border: #334155;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg-main);
            color: var(--text);
            display: flex;
            flex-direction: column;
            align-items: center;
            min-height: 100vh;
            padding: 12px;
            user-select: none;
        }}
        .header {{
            width: 100%;
            max-width: 440px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 12px;
            background: var(--bg-card);
            border-radius: 12px;
            border: 1px solid var(--border);
            margin-bottom: 12px;
        }}
        .title {{ font-size: 16px; font-weight: 700; color: #60a5fa; }}
        .badge {{
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            background: var(--success);
            color: #fff;
        }}
        .status-card {{
            width: 100%;
            max-width: 440px;
            background: var(--bg-card);
            border-radius: 12px;
            border: 1px solid var(--border);
            padding: 12px;
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 8px;
            text-align: center;
            margin-bottom: 12px;
        }}
        .stat-item {{ background: var(--bg-btn); padding: 8px; border-radius: 8px; }}
        .stat-label {{ font-size: 11px; color: var(--text-dim); text-transform: uppercase; }}
        .stat-val {{ font-size: 16px; font-weight: bold; color: var(--text); margin-top: 2px; }}

        /* Step selector */
        .step-bar {{
            width: 100%;
            max-width: 440px;
            display: flex;
            gap: 6px;
            margin-bottom: 12px;
        }}
        .step-btn {{
            flex: 1;
            padding: 8px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            color: var(--text);
            border-radius: 8px;
            font-weight: 600;
            font-size: 13px;
            cursor: pointer;
        }}
        .step-btn.active {{
            background: var(--accent);
            border-color: #60a5fa;
        }}

        /* D-Pad Jog */
        .d-pad-container {{
            width: 100%;
            max-width: 440px;
            background: var(--bg-card);
            border-radius: 16px;
            border: 1px solid var(--border);
            padding: 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
            margin-bottom: 12px;
        }}
        .d-pad {{
            display: grid;
            grid-template-columns: 80px 80px 80px;
            grid-template-rows: 80px 80px 80px;
            gap: 8px;
            margin: 8px 0;
        }}
        .jog-btn {{
            background: var(--bg-btn);
            border: 1px solid var(--border);
            border-radius: 12px;
            color: var(--text);
            font-size: 24px;
            font-weight: bold;
            display: flex;
            justify-content: center;
            align-items: center;
            cursor: pointer;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            transition: all 0.1s;
        }}
        .jog-btn:active {{
            background: var(--accent);
            transform: scale(0.95);
        }}
        .jog-center {{
            background: var(--border);
            font-size: 14px;
            color: var(--text-dim);
        }}

        /* Quick actions */
        .actions-grid {{
            width: 100%;
            max-width: 440px;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin-bottom: 12px;
        }}
        .action-btn {{
            padding: 12px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 10px;
            color: var(--text);
            font-size: 14px;
            font-weight: 600;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            cursor: pointer;
        }}
        .action-btn:active {{ background: var(--bg-btn-hover); }}
        .btn-start {{ background: var(--success); border-color: #22c55e; }}
        .btn-pause {{ background: var(--warning); color: #000; border-color: #facc15; }}
        .btn-estop {{ background: var(--danger); border-color: #ef4444; grid-column: span 2; padding: 14px; font-size: 16px; }}

        /* Console log */
        .log-box {{
            width: 100%;
            max-width: 440px;
            background: #090b0e;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 8px 12px;
            font-family: monospace;
            font-size: 12px;
            color: #4ade80;
            min-height: 48px;
            max-height: 80px;
            overflow-y: auto;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="title">⚡ MadGrav Télécommande</div>
        <div class="badge" id="dev-badge">{device_name}</div>
    </div>

    <div class="status-card">
        <div class="stat-item">
            <div class="stat-label">X</div>
            <div class="stat-val" id="val-x">0.0 mm</div>
        </div>
        <div class="stat-item">
            <div class="stat-label">Y</div>
            <div class="stat-val" id="val-y">0.0 mm</div>
        </div>
        <div class="stat-item">
            <div class="stat-label">État</div>
            <div class="stat-val" id="val-state" style="color:#4ade80;">Prêt</div>
        </div>
    </div>

    <div class="step-bar">
        <button class="step-btn" onclick="setStep(0.1, this)">0.1 mm</button>
        <button class="step-btn" onclick="setStep(1.0, this)">1 mm</button>
        <button class="step-btn active" onclick="setStep(10.0, this)">10 mm</button>
        <button class="step-btn" onclick="setStep(50.0, this)">50 mm</button>
    </div>

    <div class="d-pad-container">
        <div class="d-pad">
            <div></div>
            <button class="jog-btn" onclick="jog('Y', 1)">▲</button>
            <div></div>
            <button class="jog-btn" onclick="jog('X', -1)">◀</button>
            <button class="jog-btn jog-center" onclick="control('origin')">🎯 (0,0)</button>
            <button class="jog-btn" onclick="jog('X', 1)">▶</button>
            <div></div>
            <button class="jog-btn" onclick="jog('Y', -1)">▼</button>
            <div></div>
        </div>
    </div>

    <div class="actions-grid">
        <button class="action-btn" onclick="control('home')">🏠 Origine ($H)</button>
        <button class="action-btn" onclick="control('frame')">📐 Cadrer (Frame)</button>
        <button class="action-btn btn-start" onclick="control('start')">▶ Démarrer Job</button>
        <button class="action-btn btn-pause" onclick="control('pause')">⏸ Pause</button>
        <button class="action-btn btn-estop" onclick="control('estop')">🛑 ARRÊT D'URGENCE (E-STOP)</button>
    </div>

    <div class="log-box" id="log-box">Connecté au serveur MadGrav. Prêt.</div>

    <script>
        let currentStep = 10.0;
        const csrfToken = "{csrf_token}";

        function setStep(val, btn) {{
            currentStep = val;
            document.querySelectorAll('.step-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            log(`Pas configuré à ${{val}} mm`);
        }}

        function log(msg) {{
            const box = document.getElementById('log-box');
            box.innerText = `[${{new Date().toLocaleTimeString()}}] ${{msg}}`;
        }}

        async function jog(axis, dir) {{
            const dist = currentStep * dir;
            try {{
                const res = await fetch('/api/jog', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ axis: axis, distance: dist, csrf_token: csrfToken }})
                }});
                const data = await res.json();
                if(data.success) {{
                    log(`Jog ${{axis}} ${{dist > 0 ? '+' : ''}}${{dist}} mm`);
                    updateStatus();
                }}
            }} catch(e) {{
                log(`Erreur Jog: ${{e}}`);
            }}
        }}

        async function control(action) {{
            try {{
                const res = await fetch('/api/control', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ action: action, csrf_token: csrfToken }})
                }});
                const data = await res.json();
                log(`Action '${{action}}' exécutée: ${{data.message || 'OK'}}`);
                updateStatus();
            }} catch(e) {{
                log(`Erreur Action: ${{e}}`);
            }}
        }}

        async function updateStatus() {{
            try {{
                const res = await fetch('/api/status');
                const data = await res.json();
                if(data) {{
                    document.getElementById('val-x').innerText = (data.x || 0).toFixed(1) + ' mm';
                    document.getElementById('val-y').innerText = (data.y || 0).toFixed(1) + ' mm';
                    document.getElementById('val-state').innerText = data.status || 'Prêt';
                }}
            }} catch(e) {{}}
        }}

        setInterval(updateStatus, 1500);
        updateStatus();
    </script>
</body>
</html>
"""
