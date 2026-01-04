"""
Chỉ làm:
    parse CLI
    xác định USER (SUDO_USER > os.getuid)
    check policy
    ghi audit log
    gọi module khác

❌ Không Merkle
❌ Không chunk
❌ Không WAL
"""
import argparse
import sys
import os

# Xác định đường dẫn tuyệt đối đến thư mục gốc project (cha của src/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POLICY_FILE = os.path.join(PROJECT_ROOT, "policy.yaml")

# Import các module
from .utils import get_current_user
from .policy import PolicyManager
from .audit import AuditLogger
from .recovery import RecoveryManager
from .snapshot import SnapshotManager
from .integrity import IntegrityManager

def main():
    parser = argparse.ArgumentParser(description="Secure Backup CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. INIT
    p_init = subparsers.add_parser("init", help="Initialize backup store")
    p_init.add_argument("store_path", help="Path to create store")

    # 2. BACKUP
    p_backup = subparsers.add_parser("backup", help="Create backup")
    p_backup.add_argument("source", help="Source directory")
    p_backup.add_argument("--label", required=True, help="Snapshot description")

    # 3. LIST
    p_list = subparsers.add_parser("list-snapshots", help="List all snapshots")

    # 4. VERIFY
    p_verify = subparsers.add_parser("verify", help="Verify integrity")
    p_verify.add_argument("snapshot_id", help="ID of snapshot to verify")

    # 5. RESTORE
    p_restore = subparsers.add_parser("restore", help="Restore snapshot")
    p_restore.add_argument("snapshot_id", help="ID of snapshot")
    p_restore.add_argument("target", help="Target directory")

    # 6. AUDIT-VERIFY
    p_audit = subparsers.add_parser("audit-verify", help="Verify audit log integrity")

    args = parser.parse_args()

    # --- SETUP HỆ THỐNG ---
    # Mặc định store nằm ở ./store nếu đã init, hoặc theo tham số init
    store_path = "store" 
    if args.command == "init":
        store_path = args.store_path
    
    # Init các manager
    user = get_current_user()
    policy = PolicyManager(POLICY_FILE)  # Sử dụng đường dẫn tuyệt đối
    audit = AuditLogger(store_path)
    recovery = RecoveryManager(store_path)
    
    # Recover crash (Start-up scan)
    # Chỉ chạy logic recover nếu không phải lệnh init (vì init tạo folder mới)
    if args.command != "init":
         if os.path.exists(store_path):
             recovery.recover()
    
    # --- CHECK POLICY ---
    if not policy.check_permission(user, args.command):
        print(f"PERMISSION DENIED: User '{user}' cannot run '{args.command}'")
        # Ghi Audit log DENY
        arg_list = sys.argv[2:] # Lấy tham số sau command
        audit.log(user, args.command, arg_list, "DENY")
        sys.exit(1)

    # --- EXECUTE COMMAND ---
    status = "OK"
    try:
        # Chuẩn bị tham số để log
        arg_list = sys.argv[2:]

        if args.command == "init":
            if os.path.exists(args.store_path):
                print("Store already exists.")
                status = "FAIL"
            else:
                os.makedirs(args.store_path)
                os.makedirs(os.path.join(args.store_path, "chunks"))
                os.makedirs(os.path.join(args.store_path, "snapshots"))
                print(f"Initialized store at {args.store_path}")

        elif args.command == "backup":
            snap_mgr = SnapshotManager(store_path)
            if not os.path.exists(args.source):
                print("Source not found")
                status = "FAIL"
            else:
                snap_mgr.create_snapshot(args.source, args.label)

        elif args.command == "list-snapshots":
            if not os.path.exists(os.path.join(store_path, "snapshots")):
                print("No snapshots found.")
            else:
                snaps = sorted(os.listdir(os.path.join(store_path, "snapshots")))
                print(f"{'ID':<15} {'TIMESTAMP'}")
                print("-" * 30)
                for s in snaps:
                    if s.startswith("snapshot_"):
                        print(s.replace("snapshot_", ""))

        elif args.command == "verify":
            integrity = IntegrityManager(store_path)
            valid = integrity.verify_snapshot(args.snapshot_id)
            if not valid:
                status = "FAIL"

        elif args.command == "restore":
            integrity = IntegrityManager(store_path)
            integrity.restore(args.snapshot_id, args.target)

        elif args.command == "audit-verify":
            audit.verify_chain()

    except Exception as e:
        print(f"Runtime Error: {e}")
        status = "FAIL"
    
    # --- GHI AUDIT LOG ---
    # Luôn ghi log dù thành công hay thất bại (nhưng đã qua bước check policy)
    audit.log(user, args.command, arg_list, status)

if __name__ == "__main__":
    main()
    