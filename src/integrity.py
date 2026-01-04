"""
build Merkle root từ manifest canonical
verify snapshot
detect rollback (prev_root chain)
"""
import os
import json
import shutil
from .utils import canonical_json_dump, compute_sha256
from .storage import StorageEngine

class IntegrityManager:
    def __init__(self, store_path="store"):
        self.store_path = store_path
        self.snapshots_base = os.path.join(store_path, "snapshots")
        self.storage = StorageEngine(store_path)

    def load_snapshot(self, snap_id):
        path = os.path.join(self.snapshots_base, f"snapshot_{snap_id}")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Snapshot {snap_id} not found")
        
        with open(os.path.join(path, "manifest.json"), 'r') as f:
            manifest = json.load(f)
        with open(os.path.join(path, "metadata.json"), 'r') as f:
            metadata = json.load(f)
            
        return manifest, metadata

    def verify_snapshot(self, snap_id):
        """
        Verify 3 lớp:
        1. Tính lại Merkle Root từ Manifest -> so với Metadata.
        2. Kiểm tra tất cả Chunk có tồn tại không.
        3. Kiểm tra Rollback (Prev Root chain).
        """
        print(f"Verifying snapshot {snap_id}...")
        try:
            manifest, metadata = self.load_snapshot(snap_id)
            
            # 1. Recompute Merkle
            cal_root = compute_sha256(canonical_json_dump(manifest))
            if cal_root != metadata['merkle_root']:
                print("VERIFY FAIL: Metadata Merkle Root mismatch! Manifest might be tampered.")
                return False

            # 2. Check chunks existence AND integrity
            for file_path, chunks in manifest.items():
                for h in chunks:
                    chunk_path = os.path.join(self.store_path, "chunks", h)
                    if not os.path.exists(chunk_path):
                        print(f"VERIFY FAIL: Missing chunk {h} for file {file_path}")
                        return False
                    
                    # Verify chunk integrity by recomputing hash
                    with open(chunk_path, 'rb') as cf:
                        actual_hash = compute_sha256(cf.read())
                        if actual_hash != h:
                            print(f"VERIFY FAIL: Chunk {h} is corrupted (hash mismatch)")
                            return False

            # 3. Check Rollback (Prev Root Chain)
            # Logic: Load toàn bộ snapshot, sort, check chuỗi
            print("Checking hash chain (anti-rollback)...")
            all_snaps = sorted([s for s in os.listdir(self.snapshots_base) if s.startswith("snapshot_")])
            
            # Tìm vị trí snapshot hiện tại
            current_dir_name = f"snapshot_{snap_id}"
            if current_dir_name not in all_snaps:
                 # Should not happen
                 return False

            idx = all_snaps.index(current_dir_name)
            
            # Nếu không phải snap đầu tiên, check prev_root
            if idx > 0:
                prev_snap_name = all_snaps[idx-1]
                # Load metadata của thằng trước
                with open(os.path.join(self.snapshots_base, prev_snap_name, "metadata.json"), 'r') as f:
                    prev_meta_obj = json.load(f)
                
                if metadata['prev_root'] != prev_meta_obj['merkle_root']:
                    print(f"VERIFY FAIL: Rollback detected! Prev_root of {snap_id} does not match {prev_snap_name}")
                    return False
            
            print("VERIFY OK.")
            return True

        except Exception as e:
            print(f"VERIFY FAIL: Exception {e}")
            return False

    def restore(self, snap_id, target_path):
        """Restore dữ liệu sau khi Verify thành công."""
        if not self.verify_snapshot(snap_id):
            print("Restore aborted due to verification failure.")
            return

        print(f"Restoring snapshot {snap_id} to {target_path}...")
        manifest, _ = self.load_snapshot(snap_id)

        if os.path.exists(target_path):
            shutil.rmtree(target_path)
        os.makedirs(target_path)

        for rel_path, chunks in manifest.items():
            dest_file = os.path.join(target_path, rel_path)
            os.makedirs(os.path.dirname(dest_file), exist_ok=True)
            self.storage.restore_file(chunks, dest_file)
        
        print("Restore completed.")
        