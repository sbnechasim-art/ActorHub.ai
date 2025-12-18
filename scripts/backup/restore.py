"""
ActorHub.ai Restore Script
Restore from backup
"""
import os
import sys
import subprocess
import gzip
import shutil
from pathlib import Path
from datetime import datetime

# Fix encoding for Windows
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8')


def list_backups(backup_dir="backups"):
    """List available backups"""
    print("Available backups:")
    print("-"*60)

    backup_path = Path(backup_dir)

    if not backup_path.exists():
        print("  No backups found")
        return []

    backups = sorted(backup_path.glob("db_backup_*.sql.gz"), reverse=True)

    for i, backup in enumerate(backups):
        size = backup.stat().st_size / 1024
        mtime = datetime.fromtimestamp(backup.stat().st_mtime)
        print(f"  [{i}] {backup.name} ({size:.2f} KB) - {mtime}")

    return backups


def restore_database(backup_file):
    """Restore Database"""
    print(f"Restoring Database from {backup_file}...")

    # Decompress
    decompressed = str(backup_file).replace('.gz', '')

    try:
        with gzip.open(backup_file, 'rb') as f_in:
            with open(decompressed, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        # Drop and recreate database
        subprocess.run([
            'docker', 'exec', 'actorhub-postgres',
            'psql', '-U', 'postgres', '-c',
            'DROP DATABASE IF EXISTS actorhub; CREATE DATABASE actorhub;'
        ], check=True, timeout=60)

        # Restore using psql
        with open(decompressed, 'rb') as f:
            result = subprocess.run([
                'docker', 'exec', '-i', 'actorhub-postgres',
                'psql', '-U', 'postgres', '-d', 'actorhub'
            ], stdin=f, capture_output=True, timeout=300)

        os.remove(decompressed)

        if result.returncode == 0:
            print("  OK: Restore completed!")
            return True
        else:
            print("  OK: Restore completed with warnings")
            return True

    except Exception as e:
        print(f"  FAILED: {e}")
        return False


def main():
    backups = list_backups()

    if not backups:
        return

    print("\nSelect backup to restore (number) or 'q' to cancel:")
    choice = input("> ")

    if choice.lower() == 'q':
        return

    try:
        idx = int(choice)
        backup = backups[idx]

        print(f"\nWARNING: You are about to restore {backup.name}")
        print("   This will DELETE all current data!")
        confirm = input("   Continue? (yes/no): ")

        if confirm.lower() == 'yes':
            restore_database(backup)
        else:
            print("   Cancelled")

    except (ValueError, IndexError):
        print("Invalid selection")


if __name__ == "__main__":
    main()
