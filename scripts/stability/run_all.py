"""
ActorHub.ai Stability & Hardening Suite
Runs all security and stability checks
"""
import subprocess
import sys
import os
from datetime import datetime

# Fix encoding for Windows
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8')


def run_command(name, command):
    """Run a command and return success status"""
    print(f"\n{'='*60}")
    print(f"Running: {name}")
    print('='*60)

    result = subprocess.run(command, shell=True)
    return result.returncode == 0


def main():
    print("""
    ============================================================
         ActorHub.ai Stability & Hardening Suite
    ============================================================
    """)

    results = []

    # 1. Security Audit
    success = run_command(
        "Security Audit",
        "python tests/security/security_audit.py"
    )
    results.append(("Security Audit", success))

    # 2. Backup Test
    success = run_command(
        "Backup Test",
        "python scripts/backup/backup.py"
    )
    results.append(("Backup", success))

    # Summary
    print("\n")
    print("="*60)
    print("STABILITY SUITE RESULTS")
    print("="*60)

    all_passed = True
    for name, success in results:
        status = "PASSED" if success else "FAILED"
        icon = "OK" if success else "FAIL"
        print(f"  [{icon}] {name}: {status}")
        if not success:
            all_passed = False

    print("="*60)

    if all_passed:
        print("All checks passed!")
    else:
        print("Some checks failed!")

    print("""

    Additional Commands:

    1. Load Testing:
       locust -f tests/load/locustfile.py --host=http://localhost:8000

    2. Monitoring Stack:
       docker-compose -f docker-compose.monitoring.yml up -d
       Open: http://localhost:3001 (Grafana, admin/actorhub123)

    3. Manual Backup:
       python scripts/backup/backup.py

    4. Restore from Backup:
       python scripts/backup/restore.py
    """)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
