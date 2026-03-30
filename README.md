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
# Edit .env — add ODDS_API_KEY, set PAPER_TRADING=true, set OCI_NAMESPACE
mkdir -p data/db data/csv_cache data/backups
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

### Object Storage setup

Automated daily backups run at 04:00 UTC and upload to Oracle Object Storage.
Free tier includes 20GB — more than sufficient for daily SQLite backups.

```bash
# Get your namespace
oci os ns get

# Create backup bucket
oci os bucket create \
  --compartment-id <compartment-id> \
  --name betting-backups

# Create dynamic group for the VM instance
# In Oracle Cloud Console:
# Identity > Dynamic Groups > Create
# Rule: ANY {instance.id = '<your-instance-ocid>'}

# Create IAM policy
# Identity > Policies > Create
# Statement:
# Allow dynamic-group <group-name> to manage objects
#   in compartment <compartment> where target.bucket.name = 'betting-backups'
```

Set `OCI_NAMESPACE` in `.env` (find it with `oci os ns get`). On the Oracle Cloud VM the
scheduler authenticates automatically via instance principal — no API keys needed in the
container.

### Verify backups

```bash
# List backups in Object Storage
oci os object list --namespace <namespace> --bucket-name betting-backups

# Check local backups inside container
docker compose exec scheduler ls /data/backups/
```

## Known Constraints

- Analysis runs at 16:00 UTC — only fixtures kicking off after ~18:00 are covered
- Results fetched via Odds API scores endpoint — free tier is 500 requests/month, monitor usage as league count grows
- PL only until team name mappings are added for other leagues in `leagues.yaml`
- Paper trading mode by default — set `PAPER_TRADING=false` only when confident in signal quality