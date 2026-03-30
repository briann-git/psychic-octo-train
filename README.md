# psychic-octo-train

## Deployment

### Oracle Cloud Free Tier VM setup

1. Create account at cloud.oracle.com
2. Launch an Always Free VM:
   - Shape: VM.Standard.E2.1.Micro (1 OCPU, 1GB RAM) or
             VM.Standard.A1.Flex (2 OCPU, 12GB RAM — more generous)
   - Image: Ubuntu 22.04
   - Add SSH key
3. Open ports in the security list (not needed for this app — no inbound traffic)
4. SSH in: `ssh ubuntu@<your-ip>`

### Install Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker ubuntu
# Log out and back in
```

### Deploy

```bash
git clone <your-repo>
cd psychic-octo-train
cp .env.example .env
# Edit .env — add ODDS_API_KEY, set PAPER_TRADING=true
mkdir -p data/db data/csv_cache
docker compose up -d
```

### Verify

```bash
docker compose logs -f
```

### Updates

```bash
git pull
docker compose up -d --build
```

### Persistent storage note

SQLite database and CSV cache are mounted from `./data/` on the host VM. They survive
container restarts and redeployments. Back up `./data/db/ledger.db` periodically — this
is your entire history.

## Known Constraints

- Analysis runs at 16:00 UTC — only fixtures kicking off after ~18:00 are covered
- Results fetched via Odds API scores endpoint — free tier is 500 requests/month, monitor usage as league count grows
- PL only until team name mappings are added for other leagues in `leagues.yaml`
- Paper trading mode by default — set `PAPER_TRADING=false` only when confident in signal quality