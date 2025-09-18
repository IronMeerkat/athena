import os
import signal
import subprocess
import sys
import time

def cleanup_old_workers():
    """Clean up old Celery workers"""
    try:
        # Get all Celery worker process IDs
        result = subprocess.run(
            ["pgrep", "-f", "celery.*worker"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print("No existing Celery workers found.")
            return

        pids = [int(pid.strip()) for pid in result.stdout.strip().split('\n') if pid.strip()]

        if not pids:
            print("No existing Celery workers found.")
            return

        print(f"Found {len(pids)} existing Celery worker(s). Cleaning up...")

        # Send SIGTERM to all workers
        for pid in pids:
            try:
                print(f"Terminating worker {pid}...")
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                print(f"Worker {pid} already terminated")
            except Exception as e:
                print(f"Error terminating worker {pid}: {e}")

        # Wait for graceful shutdown
        print("Waiting 3 seconds for graceful shutdown...")
        time.sleep(3)

        # Check for remaining workers
        remaining_result = subprocess.run(
            ["pgrep", "-f", "celery.*worker"],
            capture_output=True,
            text=True
        )

        if remaining_result.returncode == 0:
            remaining_pids = [int(pid.strip()) for pid in remaining_result.stdout.strip().split('\n') if pid.strip()]
            if remaining_pids:
                print(f"Force killing {len(remaining_pids)} stubborn workers...")
                for pid in remaining_pids:
                    try:
                        os.kill(pid, signal.SIGKILL)
                        print(f"Force killed worker {pid}")
                    except ProcessLookupError:
                        pass
                    except Exception as e:
                        print(f"Error force killing worker {pid}: {e}")

        print("Cleanup completed.")

    except Exception as e:
        print(f"Error during cleanup: {e}")
        sys.exit(1)

