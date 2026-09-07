# Deploy the bot 24/7 on a CPU VPS (text chat + Gemini proxy)

Runs the **text-chat** bot + the **Gemini proxy** (cli-proxy-api) 24/7 via systemd.
Voice (XTTS) stays **off** on the VPS (CPU + RAM) — keep it on the home GPU box.

Assumes the VPS is **Linux x86_64** (Ubuntu/Debian) with your normal user + sudo.
(ARM VPS: the `cli-proxy-api` binary won't run — re-download the ARM build on the VPS.)

---

## A. Home box (WSL) — build + copy the bundle

```bash
bash ~/projects/callsign/deploy/make-bundle.sh
scp ~/callsign-deploy.tgz USER@VPS_IP:~/
```

The bundle has: bot code, a text-only `.env` (your real Discord token + Gemini key,
`VOICE_ENABLED=false`), and the Gemini proxy (binary + `config.yaml` + auth).

---

## B. VPS — one-time setup

```bash
# 1) unpack
cd ~ && tar xzf callsign-deploy.tgz
mv ~/callsign-deploy/callsign   ~/callsign
mkdir -p ~/cliproxy && mv ~/callsign-deploy/cliproxy/* ~/cliproxy/
mv ~/callsign-deploy/dot-cli-proxy-api  ~/.cli-proxy-api
chmod +x ~/cliproxy/cli-proxy-api
rm -rf ~/callsign-deploy

# 2) system deps
sudo apt update && sudo apt install -y python3-venv python3-pip

# 3) bot venv + LIGHT deps (no torch/coqui — voice is off)
cd ~/callsign
python3 -m venv .venv
.venv/bin/pip install -U pip wheel
.venv/bin/pip install -r requirements-text.txt
.venv/bin/pip install -e .

# 4) sanity: proxy starts + serves models
cd ~/cliproxy && ./cli-proxy-api -config config.yaml &   # Ctrl-C after the check
sleep 4
KEY=$(grep -oE 'sk-[A-Za-z0-9-]+' ~/cliproxy/config.yaml | head -1)
curl -s http://127.0.0.1:8317/v1/models -H "Authorization: Bearer $KEY" | head -c 200
kill %1 2>/dev/null
```

If `/v1/models` lists models → proxy works. If it says auth error, the antigravity
token may need a fresh login on this machine (run `./cli-proxy-api` interactively and
follow its login prompt), then retry.

---

## C. VPS — systemd services (24/7 + auto-restart + start on boot)

```bash
U=$(whoami); H=$HOME

sudo tee /etc/systemd/system/cli-proxy-api.service >/dev/null <<EOF
[Unit]
Description=cli-proxy-api (Gemini via Antigravity)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$U
WorkingDirectory=$H/cliproxy
ExecStart=$H/cliproxy/cli-proxy-api -config $H/cliproxy/config.yaml
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/callsign-bot.service >/dev/null <<EOF
[Unit]
Description=callsign Discord bot (text mode)
After=network-online.target cli-proxy-api.service
Wants=network-online.target
Requires=cli-proxy-api.service

[Service]
Type=simple
User=$U
WorkingDirectory=$H/callsign
ExecStart=$H/callsign/.venv/bin/python -u -m callsign.text_app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now cli-proxy-api.service
sudo systemctl enable --now callsign-bot.service
```

---

## D. Verify

```bash
systemctl status cli-proxy-api.service --no-pager
systemctl status callsign-bot.service --no-pager
journalctl -u callsign-bot.service -n 30 --no-pager   # expect "logged in as … ready"
```

Then in Discord: `@YourBot co tam?` → it replies (text). It survives reboots and crashes.

---

## Updating later

Rebuild the bundle at home, copy over, then on the VPS:
```bash
# replace code (keep .env), then:
sudo systemctl restart callsign-bot.service
```

## Notes

- **Secrets** live only in `~/callsign/.env` and `~/.cli-proxy-api/` on the VPS.
- **Persona:** edit `~/callsign/persona.md`, then in Discord `!reload` (no restart).
- **Switch model:** `.env` `LLM_MODEL=gemini-3.1-flash-lite` (faster) etc., then
  `sudo systemctl restart callsign-bot.service`.
- **Enable voice on the VPS later** (slow on CPU): `pip install -r requirements.txt` +
  CPU torch (`pip install torch --index-url https://download.pytorch.org/whl/cpu`), copy
  `voiceprint/latents.pt` from home, set `VOICE_ENABLED=true`, restart.
