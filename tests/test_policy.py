# tests/test_policy.py
import unittest
import os
import shutil
import subprocess

# Đường dẫn file
POLICY_FILE = "policy.yaml"
BACKUP_POLICY = "policy.yaml.bak"

class TestPolicy(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # 1. Backup file policy thật
        if os.path.exists(POLICY_FILE):
            shutil.copy(POLICY_FILE, BACKUP_POLICY)
        
        # 2. Lấy tên user hiện tại đang chạy test
        import getpass
        cls.current_user = getpass.getuser()
        
    @classmethod
    def tearDownClass(cls):
        # Restore file policy thật sau khi test xong
        if os.path.exists(BACKUP_POLICY):
            shutil.move(BACKUP_POLICY, POLICY_FILE)

    def create_policy(self, role):
        """Tạo file policy tạm thời gán user hiện tại vào role mong muốn"""
        content = f"""
users:
  {self.current_user}: {role}

roles:
  admin:
    - init
    - list-snapshots
  auditor:
    - list-snapshots
"""
        with open(POLICY_FILE, 'w') as f:
            f.write(content)

    def test_admin_permission(self):
        """Test: Admin được phép chạy init"""
        self.create_policy("admin")
        
        # Chạy lệnh init (mong đợi thành công - exit code 0)
        result = subprocess.run(
            ["python3", "-m", "src.main", "init", "store"],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, "Admin should be able to init")
        print("\n[PASS] Admin permission test")

    def test_auditor_denial(self):
        """Test: Auditor KHÔNG được phép chạy init"""
        self.create_policy("auditor")
        
        # Chạy lệnh init (mong đợi thất bại - exit code 1)
        result = subprocess.run(
            ["python3", "-m", "src.main", "init", "store_fail"],
            capture_output=True, text=True
        )
        
        self.assertNotEqual(result.returncode, 0, "Auditor should NOT be able to init")
        self.assertIn("PERMISSION DENIED", result.stdout, "Output should contain denial message")
        print("[PASS] Auditor denial test")

if __name__ == '__main__':

    # Cleanup store tạm nếu có
    if os.path.exists("store"):
        shutil.rmtree("store")
    print("========================================")
    print("=== TEST POLICY ===")
    print("========================================")
    unittest.main()