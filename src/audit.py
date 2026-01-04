import os
import time
from .utils import compute_string_sha256

AUDIT_FILE = "store/audit.log"

class AuditLogger:
    def __init__(self, store_path="store"):
        self.log_path = os.path.join(store_path, "audit.log")

    def get_last_hash(self):
        """Đọc dòng cuối cùng để lấy ENTRY_HASH làm PREV_HASH cho dòng mới."""
        if not os.path.exists(self.log_path):
            return "0" * 64  # Genesis hash (all zeros)
        
        try:
            with open(self.log_path, 'r') as f:
                lines = f.readlines()
                if not lines:
                    return "0" * 64
                last_line = lines[-1].strip()
                # Format: ENTRY_HASH PREV_HASH ...
                parts = last_line.split()
                if len(parts) >= 1:
                    return parts[0]
                return "0" * 64
        except:
            return "0" * 64

    def log(self, user, command, args_list, status):
        """
        Ghi 1 dòng log chuẩn định dạng:
        ENTRY_HASH PREV_HASH UNIX_MS USER COMMAND ARGS_SHA256 STATUS
        """
        prev_hash = self.get_last_hash()
        unix_ms = str(int(time.time() * 1000))
        
        # Join args và hash
        args_str = " ".join(args_list)
        args_sha256 = compute_string_sha256(args_str)
        
        # Tạo nội dung raw để tính hash hiện tại
        # Lưu ý: ENTRY_HASH là hash của toàn bộ nội dung còn lại
        raw_content = f"{prev_hash} {unix_ms} {user} {command} {args_sha256} {status}"
        entry_hash = compute_string_sha256(raw_content)
        
        log_line = f"{entry_hash} {raw_content}\n"
        
        # Append-only write
        with open(self.log_path, 'a') as f:
            f.write(log_line)

    def verify_chain(self):
        """Lệnh audit-verify: kiểm tra tính toàn vẹn của chuỗi hash."""
        if not os.path.exists(self.log_path):
            print("Audit log not found.")
            return

        print("Verifying audit log...")
        expected_prev = "0" * 64
        line_num = 1
        
        with open(self.log_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) < 7:
                    print(f"AUDIT CORRUPTED at line {line_num}: Invalid format.")
                    return

                entry_hash = parts[0]
                prev_hash_in_log = parts[1]
                content_rest = " ".join(parts[1:])
                
                # 1. Kiểm tra chuỗi hash (Prev hash dòng này = Entry hash dòng trước)
                if prev_hash_in_log != expected_prev:
                    print(f"AUDIT CORRUPTED at line {line_num}: Broken chain.")
                    print(f"Expected prev: {expected_prev}")
                    print(f"Actual prev:   {prev_hash_in_log}")
                    return

                # 2. Tính lại hash dòng này xem có khớp entry_hash không
                cal_hash = compute_string_sha256(content_rest)
                if cal_hash != entry_hash:
                    print(f"AUDIT CORRUPTED at line {line_num}: Content modified.")
                    return
                
                expected_prev = entry_hash
                line_num += 1
        
        print(f"AUDIT OK. Head Hash: {expected_prev}")
        