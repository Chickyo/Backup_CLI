"""
ghi journal:
    BEGIN
    records
    COMMIT
startup scan journal
rollback snapshot chưa commit
"""
import os

JOURNAL_FILE = "journal.log"

class RecoveryManager:
    def __init__(self, store_path="store"):
        self.store_path = store_path
        self.journal_path = os.path.join(store_path, JOURNAL_FILE)

    def log_begin(self, snapshot_id):
        """Ghi BEGIN <snapshot_id>"""
        with open(self.journal_path, 'a') as f:
            f.write(f"BEGIN {snapshot_id}\n")
            f.flush()
            os.fsync(f.fileno())

    def log_commit(self, snapshot_id):
        """Ghi COMMIT <snapshot_id>"""
        with open(self.journal_path, 'a') as f:
            f.write(f"COMMIT {snapshot_id}\n")
            f.flush()
            os.fsync(f.fileno())

    def recover(self):
        """
        Quét journal khi khởi động.
        Nếu thấy BEGIN mà không có COMMIT -> Xoá thư mục snapshot rác.
        """
        if not os.path.exists(self.journal_path):
            return

        begins = set()
        commits = set()

        with open(self.journal_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) < 2: continue
                action, snap_id = parts[0], parts[1]
                
                if action == "BEGIN":
                    begins.add(snap_id)
                elif action == "COMMIT":
                    commits.add(snap_id)
        
        # Tìm các snapshot chưa commit (Dangling)
        dangling_snaps = begins - commits
        
        if dangling_snaps:
            print("Crash detected! Rolling back incomplete snapshots...")
            for snap_id in dangling_snaps:
                snap_dir = os.path.join(self.store_path, "snapshots", f"snapshot_{snap_id}")
                if os.path.exists(snap_dir):
                    print(f" - Deleting incomplete snapshot: {snap_dir}")
                    import shutil
                    shutil.rmtree(snap_dir) # Xoá thư mục snapshot lỗi
            print("Recovery complete.")
            