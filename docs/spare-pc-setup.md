# Spare PC Setup Guide (Windows -> Ubuntu Server)

This guide sets up your unused Windows PC as a reliable home server for this project.

## Goal

Run the scheduler continuously with Docker Compose, keep data persistent, and avoid Oracle/cloud lock-in.

## 1. Before You Start (on Windows)

1. Back up anything important from the PC.
2. Download Ubuntu Server 24.04 LTS ISO from Ubuntu.
3. Create a bootable USB with Rufus:
   - Partition scheme: GPT
   - Target system: UEFI
4. Wi-Fi is fine for this workload; Ethernet is optional.
5. Router admin access is optional (only needed to pin a stable LAN IP via DHCP reservation).

## 2. BIOS/UEFI Prep

1. Reboot and enter BIOS/UEFI.
2. Enable UEFI mode.
3. Set USB first in boot order.
4. Disable Fast Boot if USB boot is inconsistent.
5. Boot from USB installer.

## 3. Install Ubuntu Server 24.04 LTS

1. Choose language and keyboard.
2. Configure network (Wi-Fi or Ethernet both work).
3. Choose storage:
   - Dedicated server: use full disk.
   - Encryption: optional but recommended.
4. Create host/user:
   - Hostname example: `betting-server`
   - Username example: `brian`
5. Select and install OpenSSH Server when prompted.
6. Finish install and reboot (remove USB).

## 4. First Boot Hardening

SSH in from another machine:

```bash
ssh brian@<server-ip>
```

Update system:

```bash
sudo apt update
sudo apt full-upgrade -y
sudo reboot
```

Reconnect and enable firewall:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw enable
sudo ufw status
```

Enable security auto-updates (recommended):

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

## 5. Set Stable LAN IP

1. Preferred: in your router, create a DHCP reservation for this server.
2. If you cannot access router admin, use either:
   - hostname access on local Wi-Fi (for example `ssh brian@betting-server.local`), or
   - Tailscale (recommended) for a stable private address.
3. Keep SSH local LAN or Tailscale-only.
4. Avoid exposing ports publicly unless required.

## 6. Install Docker + Compose Plugin

Install prerequisites:

```bash
sudo apt install -y ca-certificates curl gnupg
```

Add Docker GPG key and repo:

```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

Install Docker Engine + Compose plugin:

```bash
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Use Docker without sudo:

```bash
sudo usermod -aG docker $USER
newgrp docker
```

Verify:

```bash
docker --version
docker compose version
```

## 7. Deploy This Project

Create app folder and clone:

```bash
sudo mkdir -p /srv
sudo chown $USER:$USER /srv
cd /srv
git clone https://github.com/briann-git/psychic-octo-train.git
cd psychic-octo-train
```

Create environment file:

```bash
cp .env.example .env
```

Edit `.env` and set at least:

- `ODDS_API_KEY=<your key>`
- `PAPER_TRADING=true`
- `BETTING_LEAGUES_CONFIG=config/leagues.yaml`
- `BETTING_MARKETS_CONFIG=config/markets.yaml`

Create persistent directories:

```bash
mkdir -p data/db data/csv_cache data/backups
```

Build and start:

```bash
docker compose up -d --build
```

Check service logs:

```bash
docker compose logs -f --tail=200 scheduler
```

## 8. Reboot Persistence Check

Enable Docker on boot:

```bash
sudo systemctl enable docker
sudo systemctl status docker
```

Reboot and verify app returns:

```bash
sudo reboot
# after reconnect
cd /srv/psychic-octo-train
docker compose ps
```

Note: `docker-compose.yml` already sets `restart: always` for the scheduler service.

## 9. Tailscale Setup (Recommended)

Tailscale gives you secure remote access without opening router ports.

Install on the Ubuntu server:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Install Tailscale on your laptop/phone too, and sign into the same account.

Check server Tailscale IP:

```bash
tailscale ip -4
```

SSH over Tailscale:

```bash
ssh brian@<tailscale-ip>
```

Notes:

1. If you are on the same Wi-Fi, direct LAN SSH still works (`ssh brian@<server-lan-ip>`).
2. Tailscale is mainly for remote access when away from home.
3. Keep `ufw allow OpenSSH` enabled; do not open router port forwarding unless you explicitly need public SSH.

## 10. Backups (Minimum Setup)

Back up these paths daily:

- `data/db/ledger.db`
- `config/leagues.yaml`
- `config/markets.yaml`
- `.env`

Suggested strategy:

1. Local daily backup to `data/backups/`
2. Offsite sync to B2/S3 via `rclone` or `restic`
3. Keep retention: 7 daily, 4 weekly, 3 monthly

## 11. Routine Operations

Update code and redeploy:

```bash
cd /srv/psychic-octo-train
git pull
docker compose up -d --build
```

Check status:

```bash
docker compose ps
docker compose logs --tail=100 scheduler
```

Stop/start:

```bash
docker compose stop
docker compose start
```

## 12. Troubleshooting

Container not running:

```bash
docker compose ps
docker compose logs --tail=200 scheduler
```

Permission issue on data folders:

```bash
sudo chown -R $USER:$USER /srv/psychic-octo-train
```

Docker group not applied:

```bash
newgrp docker
```

## Done Criteria

You are done when all are true:

1. `docker compose ps` shows `scheduler` as running.
2. Logs show scheduled jobs executing without fatal errors.
3. Reboot test succeeds and service comes back automatically.
4. Daily backups are confirmed.
5. You can SSH in either from local Wi-Fi or via Tailscale.
