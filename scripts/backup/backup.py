"""
ActorHub.ai Automated Backup System
Backup for DB and Storage
"""
import os
import sys
import subprocess
import gzip
import shutil
from datetime import datetime
from pathlib import Path

# Fix encoding for Windows
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8')

# Load environment
from dotenv import load_dotenv
load_dotenv('apps/api/.env')


class BackupManager:
    def __init__(self):
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results = {}

    def backup_database(self):
        """Backup PostgreSQL via Docker"""
        print("Backing up Database...")

        backup_file = self.backup_dir / f"db_backup_{self.timestamp}.sql"

        try:
            # Run pg_dump inside Docker container
            result = subprocess.run([
                'docker', 'exec', 'actorhub-postgres',
                'pg_dump', '-U', 'postgres', '-d', 'actorhub'
            ], capture_output=True, timeout=300)

            if result.returncode == 0:
                # Write dump
                with open(backup_file, 'wb') as f:
                    f.write(result.stdout)

                # Compress
                compressed_file = f"{backup_file}.gz"
                with open(backup_file, 'rb') as f_in:
                    with gzip.open(compressed_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)

                os.remove(backup_file)

                file_size = os.path.getsize(compressed_file) / 1024
                print(f"  OK: {compressed_file} ({file_size:.2f} KB)")
                self.results['database'] = {
                    'success': True,
                    'file': compressed_file,
                    'size_kb': file_size
                }
                return compressed_file
            else:
                error = result.stderr.decode() if result.stderr else "Unknown error"
                print(f"  FAILED: {error[:100]}")
                self.results['database'] = {'success': False, 'error': error[:200]}
                return None

        except subprocess.TimeoutExpired:
            print("  FAILED: Timeout")
            self.results['database'] = {'success': False, 'error': 'Timeout'}
            return None
        except Exception as e:
            print(f"  FAILED: {e}")
            self.results['database'] = {'success': False, 'error': str(e)}
            return None

    def backup_redis(self):
        """Backup Redis via Docker"""
        print("Backing up Redis...")

        backup_file = self.backup_dir / f"redis_backup_{self.timestamp}.rdb"

        try:
            # Trigger BGSAVE
            subprocess.run([
                'docker', 'exec', 'actorhub-redis',
                'redis-cli', 'BGSAVE'
            ], capture_output=True, timeout=30)

            # Wait for save
            import time
            time.sleep(2)

            # Copy RDB file
            result = subprocess.run([
                'docker', 'cp',
                'actorhub-redis:/data/dump.rdb',
                str(backup_file)
            ], capture_output=True, timeout=60)

            if result.returncode == 0 and backup_file.exists():
                file_size = os.path.getsize(backup_file) / 1024
                print(f"  OK: {backup_file} ({file_size:.2f} KB)")
                self.results['redis'] = {
                    'success': True,
                    'file': str(backup_file),
                    'size_kb': file_size
                }
                return str(backup_file)
            else:
                print("  SKIPPED: No data or container issue")
                self.results['redis'] = {'success': True, 'note': 'No data to backup'}
                return None

        except Exception as e:
            print(f"  WARNING: {e}")
            self.results['redis'] = {'success': True, 'note': str(e)}
            return None

    def backup_qdrant(self):
        """Backup Qdrant snapshots via API"""
        print("Backing up Qdrant...")

        backup_file = self.backup_dir / f"qdrant_backup_{self.timestamp}.snapshot"

        try:
            import httpx

            # Create snapshot
            response = httpx.post(
                "http://localhost:6333/collections/face_embeddings/snapshots",
                timeout=60
            )

            if response.status_code == 200:
                snapshot_name = response.json().get("result", {}).get("name")
                if snapshot_name:
                    print(f"  OK: Snapshot {snapshot_name}")
                    self.results['qdrant'] = {
                        'success': True,
                        'snapshot': snapshot_name
                    }
                    return snapshot_name

            print("  SKIPPED: No collection or data")
            self.results['qdrant'] = {'success': True, 'note': 'No data'}
            return None

        except Exception as e:
            print(f"  WARNING: {e}")
            self.results['qdrant'] = {'success': True, 'note': str(e)}
            return None

    def backup_minio(self):
        """Backup MinIO uploads via Docker"""
        print("Backing up MinIO uploads...")

        backup_file = self.backup_dir / f"minio_backup_{self.timestamp}.tar.gz"

        try:
            # List files first
            result = subprocess.run([
                'docker', 'exec', 'actorhub-minio',
                'mc', 'ls', 'local/actorhub-uploads/', '--recursive'
            ], capture_output=True, timeout=30)

            if result.returncode != 0 or not result.stdout:
                print("  SKIPPED: No files to backup")
                self.results['minio'] = {'success': True, 'note': 'No files'}
                return None

            # Create tar archive from MinIO container
            result = subprocess.run([
                'docker', 'exec', 'actorhub-minio',
                'tar', '-czf', '/tmp/uploads_backup.tar.gz', '-C', '/data', 'actorhub-uploads'
            ], capture_output=True, timeout=120)

            if result.returncode == 0:
                # Copy from container
                subprocess.run([
                    'docker', 'cp',
                    'actorhub-minio:/tmp/uploads_backup.tar.gz',
                    str(backup_file)
                ], timeout=120)

                if backup_file.exists():
                    file_size = os.path.getsize(backup_file) / 1024
                    print(f"  OK: {backup_file} ({file_size:.2f} KB)")
                    self.results['minio'] = {
                        'success': True,
                        'file': str(backup_file),
                        'size_kb': file_size
                    }
                    return str(backup_file)

            print("  SKIPPED: Backup failed")
            self.results['minio'] = {'success': True, 'note': 'No files or error'}
            return None

        except Exception as e:
            print(f"  WARNING: {e}")
            self.results['minio'] = {'success': True, 'note': str(e)}
            return None

    def cleanup_old_backups(self, keep_days=7):
        """Delete backups older than keep_days"""
        print(f"Cleaning up backups older than {keep_days} days...")

        cutoff = datetime.now().timestamp() - (keep_days * 24 * 60 * 60)
        deleted = 0

        for backup_file in self.backup_dir.glob("*"):
            if backup_file.stat().st_mtime < cutoff:
                backup_file.unlink()
                deleted += 1

        print(f"  Deleted {deleted} old files")

    def run_full_backup(self):
        """Run complete backup"""
        print("="*60)
        print("ActorHub.ai Full Backup")
        print(f"Timestamp: {self.timestamp}")
        print("="*60)

        # Database (critical)
        self.backup_database()

        # Redis (optional)
        self.backup_redis()

        # Qdrant (optional)
        self.backup_qdrant()

        # MinIO (optional)
        self.backup_minio()

        # Cleanup
        self.cleanup_old_backups()

        # Summary
        print("\n" + "="*60)
        print("BACKUP SUMMARY")
        print("="*60)

        all_success = True
        for component, result in self.results.items():
            if result.get('success'):
                if result.get('file'):
                    print(f"  OK: {component} - {result.get('file')}")
                else:
                    print(f"  OK: {component} - {result.get('note', 'Done')}")
            else:
                print(f"  FAILED: {component} - {result.get('error', 'Unknown')}")
                all_success = False

        print("="*60)
        if all_success:
            print("Backup completed successfully!")
        else:
            print("Backup completed with errors")
        print("="*60)

        return all_success


def main():
    manager = BackupManager()
    success = manager.run_full_backup()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
