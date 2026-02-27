#!/usr/bin/env bash
set -euo pipefail

CF_BIN="${CF_BIN:-/home/ultron/.local/bin/cloudflared}"
TUNNEL_NAME="${TUNNEL_NAME:-ultron-global}"
HUB_HOSTNAME="${HUB_HOSTNAME:-hub.yourdomain.com}"
BRAIN_HOSTNAME="${BRAIN_HOSTNAME:-brain.yourdomain.com}"
SSH_HOSTNAME="${SSH_HOSTNAME:-ssh.yourdomain.com}"
CF_DIR="${HOME}/.cloudflared"
CF_CONFIG="${CF_DIR}/config.yml"
SYSTEMD_DIR="${HOME}/.config/systemd/user"
SERVICE_FILE="${SYSTEMD_DIR}/cloudflared.service"

if [[ ! -x "${CF_BIN}" ]]; then
  echo "cloudflared binary not found at ${CF_BIN}"
  echo "Install first, e.g. curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o ${CF_BIN}"
  exit 1
fi

mkdir -p "${CF_DIR}" "${SYSTEMD_DIR}"

if [[ ! -f "${CF_DIR}/cert.pem" ]]; then
  echo "Missing ${CF_DIR}/cert.pem"
  echo "Run first: ${CF_BIN} tunnel login"
  exit 1
fi

existing_tunnel_id="$(${CF_BIN} tunnel list 2>/dev/null | awk -v n="${TUNNEL_NAME}" '$2==n {print $1; exit}')"
if [[ -z "${existing_tunnel_id}" ]]; then
  create_out="$(${CF_BIN} tunnel create "${TUNNEL_NAME}")"
  existing_tunnel_id="$(echo "${create_out}" | grep -Eo '[0-9a-fA-F-]{36}' | head -n1)"
fi

if [[ -z "${existing_tunnel_id}" ]]; then
  echo "Failed to resolve tunnel ID for ${TUNNEL_NAME}"
  exit 1
fi

credentials_file="${CF_DIR}/${existing_tunnel_id}.json"
if [[ ! -f "${credentials_file}" ]]; then
  echo "Expected credentials file not found: ${credentials_file}"
  exit 1
fi

cat > "${CF_CONFIG}" <<EOF
tunnel: ${existing_tunnel_id}
credentials-file: ${credentials_file}
ingress:
  - hostname: ${HUB_HOSTNAME}
    service: http://localhost:5000
  - hostname: ${BRAIN_HOSTNAME}
    service: http://localhost:11434
  - hostname: ${SSH_HOSTNAME}
    service: ssh://localhost:22
  - service: http_status:404
EOF

${CF_BIN} tunnel route dns "${TUNNEL_NAME}" "${HUB_HOSTNAME}"
${CF_BIN} tunnel route dns "${TUNNEL_NAME}" "${BRAIN_HOSTNAME}"
${CF_BIN} tunnel route dns "${TUNNEL_NAME}" "${SSH_HOSTNAME}"

cat > "${SERVICE_FILE}" <<EOF
[Unit]
Description=Cloudflare Tunnel (hub + brain + ssh)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=${CF_BIN} tunnel --config ${CF_CONFIG} run
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now cloudflared.service
systemctl --user is-active cloudflared.service

echo
echo "Tunnel is active."
echo "Hub URL:   https://${HUB_HOSTNAME}"
echo "Brain URL: https://${BRAIN_HOSTNAME}"
echo "SSH host:  ${SSH_HOSTNAME}"
