#!/usr/bin/env bash
# Build ~/callsign-deploy.tgz on the HOME box (WSL) to copy to the VPS.
# Text-only 24/7 deploy: bot code + text .env + Gemini proxy (binary+config+auth).
set -euo pipefail

SRC="$HOME/projects/callsign"
STAGE="$HOME/callsign-deploy"
rm -rf "$STAGE"; mkdir -p "$STAGE"

# 1) bot code (skip venv / git / caches / voice data)
# NOTE: --exclude must come BEFORE the operand for GNU tar.
( cd "$HOME/projects" && tar cf - \
    --exclude='callsign/.venv' \
    --exclude='callsign/.git' \
    --exclude='__pycache__' \
    --exclude='callsign/voiceprint' \
    --exclude='*.egg-info' \
    callsign ) | ( cd "$STAGE" && tar xf - )

# 2) VPS .env = local .env forced to text-only + local proxy URL
cp "$SRC/.env" "$STAGE/callsign/.env"
ENV="$STAGE/callsign/.env"
if grep -q '^VOICE_ENABLED=' "$ENV"; then
  sed -i 's#^VOICE_ENABLED=.*#VOICE_ENABLED=false#' "$ENV"
else
  echo 'VOICE_ENABLED=false' >> "$ENV"
fi
if grep -q '^OPENAI_BASE_URL=' "$ENV"; then
  sed -i 's#^OPENAI_BASE_URL=.*#OPENAI_BASE_URL=http://127.0.0.1:8317/v1#' "$ENV"
else
  echo 'OPENAI_BASE_URL=http://127.0.0.1:8317/v1' >> "$ENV"
fi

# 3) Gemini proxy: binary + config + antigravity auth
mkdir -p "$STAGE/cliproxy"
cp "$HOME/cliproxy/cli-proxy-api" "$HOME/cliproxy/config.yaml" "$STAGE/cliproxy/"
cp -r "$HOME/.cli-proxy-api" "$STAGE/dot-cli-proxy-api"

# 4) tarball
tar czf "$HOME/callsign-deploy.tgz" -C "$HOME" callsign-deploy
echo "built: $HOME/callsign-deploy.tgz ($(du -h "$HOME/callsign-deploy.tgz" | cut -f1))"
echo "next:  scp $HOME/callsign-deploy.tgz USER@VPS_IP:~/"
