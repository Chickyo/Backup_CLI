"""
chunk file (fixed-size, vd 1MiB)
hash SHA-256
lưu chunk theo hash
dedup tự nhiên
"""
import os
import shutil
from .utils import compute_sha256

CHUNK_SIZE = 1024 * 1024  # 1 MiB

class StorageEngine:
    def __init__(self, store_path="store"):
        self.store_path = store_path
        self.chunks_dir = os.path.join(store_path, "chunks")
        os.makedirs(self.chunks_dir, exist_ok=True)

    def store_file(self, filepath):
        """
        Cắt file thành chunk, lưu vào store/chunks, trả về danh sách hash.
        Thực hiện Dedup tự nhiên (nếu chunk tồn tại thì không ghi đè).
        """
        chunk_hashes = []
        with open(filepath, 'rb') as f:
            while True:
                data = f.read(CHUNK_SIZE)
                if not data:
                    break
                
                h = compute_sha256(data)
                chunk_path = os.path.join(self.chunks_dir, h)
                
                # Dedup: Chỉ ghi nếu chưa có
                if not os.path.exists(chunk_path):
                    with open(chunk_path, 'wb') as cf:
                        cf.write(data)
                
                chunk_hashes.append(h)
        return chunk_hashes

    def restore_file(self, chunk_hashes, dest_path):
        """Tái tạo file từ danh sách chunk hash."""
        with open(dest_path, 'wb') as f:
            for h in chunk_hashes:
                chunk_path = os.path.join(self.chunks_dir, h)
                if not os.path.exists(chunk_path):
                    raise FileNotFoundError(f"Missing chunk: {h}")
                
                with open(chunk_path, 'rb') as cf:
                    f.write(cf.read())
                    