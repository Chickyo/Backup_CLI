# Hash, canonical JSON, helper chung
import hashlib
import json
import os
from typing import Dict, List

def compute_sha256(data: bytes) -> str:
    """Tính SHA-256 của dữ liệu bytes."""
    return hashlib.sha256(data).hexdigest()

def compute_string_sha256(text: str) -> str:
    """Tính SHA-256 của chuỗi string (UTF-8)."""
    return compute_sha256(text.encode('utf-8'))

def compute_file_sha256(filepath: str) -> str:
    """Tính SHA-256 của file (đọc stream để tránh tràn RAM)."""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(65536)  # 64KB buffer
            if not chunk:
                break
            sha256.update(chunk)
    return sha256.hexdigest()

def canonical_json_dump(data) -> bytes:
    """
    Chuyển object sang JSON bytes theo dạng chuẩn tắc (Canonical):
    - Sắp xếp key (sort_keys=True)
    - Không thêm khoảng trắng thừa (separators)
    Dùng để tính Merkle Root ổn định.
    """
    return json.dumps(data, sort_keys=True, separators=(',', ':')).encode('utf-8')

def _sha256_bytes(data: bytes) -> str:
    """Internal: SHA-256 helper returning hex string."""
    return hashlib.sha256(data).hexdigest()

def _concat_hex_digests(digests: List[str]) -> bytes:
    """Concatenate hex digests as raw bytes in order."""
    return b''.join(bytes.fromhex(h) for h in digests)

def merkle_root_from_manifest(manifest: Dict[str, List[str]]) -> str:
    """
    Compute a true Merkle root over files using chunk hashes.

    Steps:
    - For each file (relative path -> [chunk_hash_hex, ...]):
      file_hash = SHA256(concat(raw_bytes_of_chunk_hashes))
      leaf_hash = SHA256(path_utf8 + raw_bytes_of(file_hash))
    - Build a binary Merkle tree by pairing adjacent leaves:
      parent = SHA256(raw_bytes_of(left) + raw_bytes_of(right))
      If odd count, duplicate last.

    Returns 64-hex Merkle root, or 64 zeros if no files.
    """
    # Canonical order by path
    paths = sorted(manifest.keys())
    if not paths:
        return "0" * 64

    # Build leaves
    leaves: List[str] = []
    for path in paths:
        chunk_hashes = manifest.get(path, [])
        # Concatenate chunk digests as raw bytes; empty file -> concat of [] -> b''
        file_bytes = _concat_hex_digests(chunk_hashes)
        file_hash_hex = _sha256_bytes(file_bytes)
        leaf_bytes = path.encode('utf-8') + bytes.fromhex(file_hash_hex)
        leaf_hex = _sha256_bytes(leaf_bytes)
        leaves.append(leaf_hex)

    # Reduce via Merkle pairing
    current = leaves
    while len(current) > 1:
        if len(current) % 2 == 1:
            current.append(current[-1])
        next_level: List[str] = []
        for i in range(0, len(current), 2):
            left_b = bytes.fromhex(current[i])
            right_b = bytes.fromhex(current[i+1])
            parent_hex = _sha256_bytes(left_b + right_b)
            next_level.append(parent_hex)
        current = next_level

    return current[0]

def get_current_user():
    """
    Lấy OS User. Ưu tiên SUDO_USER nếu chạy bằng sudo.
    Logic này chống việc giả mạo danh tính trong audit log.
    """
    sudo_user = os.environ.get('SUDO_USER')
    if sudo_user:
        return sudo_user
    
    # Fallback cho user thường
    try:
        return os.getlogin()
    except:
        import getpass
        return getpass.getuser()
        