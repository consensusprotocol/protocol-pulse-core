# Cloudflare Tunnel: Ultron Global Access

This setup publishes:

- `https://hub.<your-domain>` -> `http://localhost:5000`
- `https://brain.<your-domain>` -> `http://localhost:11434`
- `ssh.<your-domain>` -> `ssh://localhost:22`

## 1) One-time Cloudflare authentication (on Ultron)

```bash
/home/ultron/.local/bin/cloudflared tunnel login
```

Authorize the machine in Cloudflare Zero Trust.

## 2) Create tunnel + DNS routes + persistent service (on Ultron)

```bash
export TUNNEL_NAME="ultron-global"
export HUB_HOSTNAME="hub.yourdomain.com"
export BRAIN_HOSTNAME="brain.yourdomain.com"
export SSH_HOSTNAME="ssh.yourdomain.com"

/home/ultron/protocol_pulse/scripts/setup_cloudflare_tunnel.sh
```

This writes:

- `~/.cloudflared/config.yml`
- `~/.config/systemd/user/cloudflared.service`

And enables:

```bash
systemctl --user enable --now cloudflared.service
```

## 3) Keep user service alive after logout (recommended)

Run once:

```bash
sudo loginctl enable-linger ultron
```

## 4) Cloudflare Access policies (dashboard)

Create three self-hosted applications:

1. `hub.yourdomain.com` (type: Self-hosted)
2. `brain.yourdomain.com` (type: Self-hosted)
3. `ssh.yourdomain.com` (type: Self-hosted SSH)

For each app, add an Allow policy with your identity provider (email/GitHub), and a Deny-all fallback.

Recommended baseline:

- Allow: your email(s) or GitHub org/team
- Require: MFA
- Session duration: 8-24h
- Block country list if desired

## 5) SSH from terminal via Cloudflare Access (MacBook)

Install cloudflared on Mac and add to `~/.ssh/config`:

```sshconfig
Host ultron-cf
  HostName ssh.yourdomain.com
  User ultron
  ProxyCommand /opt/homebrew/bin/cloudflared access ssh --hostname %h
```

Connect:

```bash
ssh ultron-cf
```

## 6) App endpoint alignment

`/home/ultron/protocol_pulse/.env` should contain:

```env
PUBLIC_HUB_URL=https://hub.yourdomain.com
PUBLIC_AI_URL=https://brain.yourdomain.com
PUBLIC_SSH_HOST=ssh.yourdomain.com
USE_DOUBLE_PIPE=false
```

Restart app service after edits:

```bash
systemctl --user restart protocol-pulse.service
```
