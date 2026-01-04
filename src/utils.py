# Hash, canonical JSON, helper chung
import hashlib
import json
import os

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
        