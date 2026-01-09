"""
build Merkle root từ manifest canonical
verify snapshot
detect rollback (prev_root chain)
"""
import os
import json
import shutil
from .utils import canonical_json_dump, compute_sha256, merkle_root_from_manifest
from .storage import StorageEngine

class IntegrityManager:
    def __init__(self, store_path="store"):
        self.store_path = store_path
        self.snapshots_base = os.path.join(store_path, "snapshots")
        self.roots_log_path = os.path.join(store_path, "roots.log")
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
            
            # 1. Recompute Merkle (true Merkle tree over files)
            cal_root = merkle_root_from_manifest(manifest)
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

            # 3. Check Rollback (Prev Root Chain with roots.log)
            print("Checking rollback protection (roots.log)...")
            
            if not os.path.exists(self.roots_log_path):
                print("VERIFY FAIL: roots.log not found! Store might be corrupted.")
                # Không cho phép backward compatibility để bảo mật tốt hơn
                return False
            
            with open(self.roots_log_path, 'r') as f:
                lines = [line.strip() for line in f if line.strip()]
            
            if not lines:
                print("VERIFY FAIL: roots.log is empty!")
                return False
            
            # Verify hash chain của roots.log (như audit.log)
            print("Verifying roots.log hash chain...")
            from .utils import compute_string_sha256
            prev_hash = "0" * 64
            roots_dict = {}  # Map root -> (index, prev_root) để O(1) lookup
            
            for idx, line in enumerate(lines):
                parts = line.split()
                if len(parts) != 3:
                    print(f"VERIFY FAIL: Invalid roots.log format at line {idx+1}")
                    return False
                
                entry_hash, logged_prev_hash, root = parts
                
                # Verify hash chain
                expected_content = f"{prev_hash} {root}"
                expected_hash = compute_string_sha256(expected_content)
                if entry_hash != expected_hash:
                    print(f"VERIFY FAIL: roots.log hash chain broken at line {idx+1}")
                    return False
                
                # Store trong dict để lookup nhanh
                roots_dict[root] = (idx, logged_prev_hash)
                prev_hash = entry_hash
            
            # Snapshot phải có root trong roots.log
            if metadata['merkle_root'] not in roots_dict:
                print("VERIFY FAIL: Merkle root not in roots.log (rollback detected)!")
                return False
            
            # Kiểm tra prev_root chain
            root_index, _ = roots_dict[metadata['merkle_root']]
            if metadata['prev_root'] != "0"*64:  # Không phải snapshot đầu tiên
                if root_index == 0:
                    print("VERIFY FAIL: First snapshot cannot have non-zero prev_root!")
                    return False
                # Lấy root trước đó từ lines
                prev_line_parts = lines[root_index - 1].split()
                prev_root_in_log = prev_line_parts[2]
                if prev_root_in_log != metadata['prev_root']:
                    print("VERIFY FAIL: prev_root chain broken!")
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
        