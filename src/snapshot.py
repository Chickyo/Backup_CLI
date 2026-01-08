"""
duyệt thư mục source
tạo canonical manifest
sinh snapshot_id
ghi metadata (label, time, merkle_root, prev_root)

=> Tạo 1 thư mục trong store/snapshots/ với tên là snapshot_<id>
chứa các file:
    manifest.json
    metadata.json
"""
import os
import time
import json
from .utils import canonical_json_dump, compute_sha256
from .storage import StorageEngine
from .recovery import RecoveryManager

class SnapshotManager:
    def __init__(self, store_path="store"):
        self.store_path = store_path
        self.snapshots_base = os.path.join(store_path, "snapshots")
        self.storage = StorageEngine(store_path)
        self.recovery = RecoveryManager(store_path)
        os.makedirs(self.snapshots_base, exist_ok=True)

    def get_latest_snapshot(self):
        """Lấy snapshot gần nhất để lấy prev_root (Chống rollback)."""
        snaps = sorted(os.listdir(self.snapshots_base))
        valid_snaps = [s for s in snaps if s.startswith("snapshot_")]
        
        if not valid_snaps:
            return None
        
        # Lấy cái cuối cùng theo tên (timestamp hoặc id tăng dần)
        last_snap_dir = os.path.join(self.snapshots_base, valid_snaps[-1])
        meta_path = os.path.join(last_snap_dir, "metadata.json")
        
        if os.path.exists(meta_path):
            with open(meta_path, 'r') as f:
                return json.load(f)
        return None

    def create_snapshot(self, source_dir, label):
        """
        Quy trình tạo Snapshot:
        1. Sinh ID
        2. Ghi WAL BEGIN
        3. Scan file -> Chunking -> Build Manifest
        4. Tính Merkle Root
        5. Ghi Metadata (kèm prev_root)
        6. Ghi WAL COMMIT
        """
        snap_id = str(int(time.time()))
        snap_dir_name = f"snapshot_{snap_id}"
        snap_full_path = os.path.join(self.snapshots_base, snap_dir_name)
        
        # 1. Recovery start
        self.recovery.log_begin(snap_id)
        
        try:
            os.makedirs(snap_full_path, exist_ok=True)
            
            manifest = {}
            # 2. Walk directory
            # Sắp xếp để đảm bảo thứ tự file trong manifest là nhất quán (Canonical requirement)
            for root, dirs, files in os.walk(source_dir):
                dirs.sort()
                files.sort()
                for file in files:
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, source_dir)
                    
                    # Chunking
                    chunk_hashes = self.storage.store_file(abs_path)
                    manifest[rel_path] = chunk_hashes

            # 3. Write Manifest
            manifest_path = os.path.join(snap_full_path, "manifest.json")
            with open(manifest_path, 'wb') as f:
                f.write(canonical_json_dump(manifest))

            # 4. Compute Merkle Root (Hash of canonical manifest)
            # Trong thiết kế đơn giản này, root là hash của file manifest JSON
            merkle_root = compute_sha256(canonical_json_dump(manifest))

            # 5. Get Prev Root (Anti-rollback)
            prev_meta = self.get_latest_snapshot()
            prev_root = prev_meta['merkle_root'] if prev_meta else "0"*64

            # 6. Write Metadata
            metadata = {
                "id": snap_id,
                "timestamp": time.time(),
                "label": label,
                "merkle_root": merkle_root,
                "prev_root": prev_root
            }
            with open(os.path.join(snap_full_path, "metadata.json"), 'wb') as f:
                f.write(canonical_json_dump(metadata))
            
            # 7. Commit
            self.recovery.log_commit(snap_id)
            print(f"Snapshot {snap_id} created successfully. Root: {merkle_root[:12]}...")
            return snap_id

        except Exception as e:
            print(f"Error creating snapshot: {e}")
            # Crash consistency: Do NOT commit. Recovery logic will clean up next run.
            raise e
            