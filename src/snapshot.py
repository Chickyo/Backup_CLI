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
import random
from .utils import canonical_json_dump, merkle_root_from_manifest, compute_string_sha256
from .storage import StorageEngine
from .recovery import RecoveryManager

class SnapshotManager:
    def __init__(self, store_path="store"):
        self.store_path = store_path
        self.snapshots_base = os.path.join(store_path, "snapshots")
        self.roots_log_path = os.path.join(store_path, "roots.log")
        self.storage = StorageEngine(store_path)
        self.recovery = RecoveryManager(store_path)
        os.makedirs(self.snapshots_base, exist_ok=True)

    def get_latest_snapshot(self):
        """Lấy merkle_root và entry_hash của snapshot cuối cùng từ roots.log"""
        if not os.path.exists(self.roots_log_path):
            return None
        
        with open(self.roots_log_path, 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
        
        if not lines:
            return None
        
        # Parse dòng cuối: ENTRY_HASH PREV_HASH [SNAPSHOT_ID] ROOT
        last_line = lines[-1]
        parts = last_line.split()
        if len(parts) == 3:
            # Old format: ENTRY_HASH PREV_HASH ROOT
            entry_hash, prev_hash, merkle_root = parts
        elif len(parts) == 4:
            # New format: ENTRY_HASH PREV_HASH SNAPSHOT_ID ROOT
            entry_hash, prev_hash, snap_id, merkle_root = parts
        else:
            return None
        
        return {
            'merkle_root': merkle_root,
            'prev_hash': entry_hash  # Entry hash của snapshot này sẽ là prev_hash của snapshot tiếp theo
        }

    def create_snapshot(self, source_dir, label):
        """
        Quy trình tạo Snapshot:
        1. Sinh ID
        2. Ghi WAL BEGIN
        3. Scan file -> Chunking -> Build Manifest
        4. Tính Merkle Root
        5. Ghi Metadata (kèm prev_root)
        6. Append root vào roots.log
        7. Ghi WAL COMMIT
        """
        # Tránh collision: timestamp + random 4 digits
        snap_id = f"{int(time.time())}_{random.randint(1000, 9999)}"
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
                dirs.sort()  # Sort in-place để os.walk traverse theo thứ tự
                files.sort()  # Sort files để đảm bảo canonical order
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

            # 4. Compute Merkle Root (True Merkle tree over files)
            merkle_root = merkle_root_from_manifest(manifest)

            # 5. Get Prev Root và Prev Hash (Anti-rollback)
            prev_meta = self.get_latest_snapshot()
            prev_root = prev_meta['merkle_root'] if prev_meta else "0"*64
            prev_hash = prev_meta['prev_hash'] if prev_meta else "0"*64

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
            
            # 7. Append root vào roots.log với hash chain (Anti-rollback + Anti-tamper)
            # Format: ENTRY_HASH PREV_HASH SNAPSHOT_ID ROOT
            entry_content = f"{prev_hash} {snap_id} {merkle_root}"
            entry_hash = compute_string_sha256(entry_content)
            log_line = f"{entry_hash} {prev_hash} {snap_id} {merkle_root}\n"
            
            with open(self.roots_log_path, 'a') as f:
                f.write(log_line)
                f.flush()
                os.fsync(f.fileno())
            
            # 8. Commit
            self.recovery.log_commit(snap_id)
            print(f"Snapshot {snap_id} created successfully. Root: {merkle_root[:12]}...")
            return snap_id

        except Exception as e:
            print(f"Error creating snapshot: {e}")
            # Crash consistency: Do NOT commit. Recovery logic will clean up next run.
            raise e
            