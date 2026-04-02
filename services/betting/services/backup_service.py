"""Backup service — copies the SQLite ledger to a local timestamped file and
uploads it to Oracle Object Storage, then prunes old copies."""

import logging
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import oci

logger = logging.getLogger(__name__)


class BackupService:
    def __init__(
        self,
        db_path: str,
        backup_dir: str,
        oci_namespace: str,
        oci_bucket: str,
        local_retention_days: int = 7,
        remote_retention_days: int = 30,
    ) -> None:
        self._db_path = Path(db_path)
        self._backup_dir = Path(backup_dir)
        self._oci_namespace = oci_namespace
        self._oci_bucket = oci_bucket
        self._local_retention_days = local_retention_days
        self._remote_retention_days = remote_retention_days
        self._backup_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> None:
        """
        1. Copy ledger.db to a timestamped local backup file
        2. Upload to Oracle Object Storage
        3. Prune old local backups
        4. Prune old remote backups
        """
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        backup_filename = f"ledger_{timestamp}.db"
        local_backup = self._backup_dir / backup_filename

        # 1. Local copy
        try:
            shutil.copy2(self._db_path, local_backup)
            logger.info("Local backup created: %s", local_backup)
        except Exception as exc:
            logger.error("Failed to create local backup: %s", exc)
            raise

        # 2. Upload — non-fatal: local backup exists as safety net
        try:
            self._upload(local_backup, backup_filename)
            logger.info("Uploaded backup to Object Storage: %s", backup_filename)
        except Exception as exc:
            logger.error("Failed to upload backup to Object Storage: %s", exc)

        # 3. Prune local
        self._prune_local()

        # 4. Prune remote
        self._prune_remote()

    def _get_client(self) -> oci.object_storage.ObjectStorageClient:
        """
        Returns an OCI Object Storage client.
        Tries instance principal auth first (used on Oracle Cloud VM).
        Falls back to config-file auth for local development.
        """
        try:
            signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
            return oci.object_storage.ObjectStorageClient(config={}, signer=signer)
        except Exception:
            logger.debug("Instance principal auth failed — falling back to config file auth")
            config = oci.config.from_file()
            return oci.object_storage.ObjectStorageClient(config=config)

    def _upload(self, local_path: Path, object_name: str) -> None:
        """Upload file to Oracle Object Storage."""
        client = self._get_client()
        with open(local_path, "rb") as f:
            client.put_object(
                namespace_name=self._oci_namespace,
                bucket_name=self._oci_bucket,
                object_name=object_name,
                put_object_body=f,
            )

    def _prune_local(self) -> None:
        """Delete local backup files older than local_retention_days."""
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=self._local_retention_days)
        for path in self._backup_dir.glob("ledger_*.db"):
            try:
                date_str = path.stem.replace("ledger_", "")
                file_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if file_date < cutoff:
                    path.unlink()
                    logger.info("Pruned local backup: %s", path.name)
            except (ValueError, OSError) as exc:
                logger.warning("Could not prune local backup %s: %s", path.name, exc)

    def _prune_remote(self) -> None:
        """Delete Object Storage objects older than remote_retention_days."""
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=self._remote_retention_days)
        try:
            client = self._get_client()
            objects = client.list_objects(
                namespace_name=self._oci_namespace,
                bucket_name=self._oci_bucket,
                prefix="ledger_",
            ).data.objects

            for obj in objects:
                try:
                    date_str = obj.name.replace("ledger_", "").replace(".db", "")
                    obj_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    if obj_date < cutoff:
                        client.delete_object(
                            namespace_name=self._oci_namespace,
                            bucket_name=self._oci_bucket,
                            object_name=obj.name,
                        )
                        logger.info("Pruned remote backup: %s", obj.name)
                except (ValueError, Exception) as exc:
                    logger.warning("Could not prune remote object %s: %s", obj.name, exc)
        except Exception as exc:
            logger.error("Failed to prune remote backups: %s", exc)
