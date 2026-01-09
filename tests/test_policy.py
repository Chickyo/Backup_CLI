# tests/test_policy.py
import unittest
import os
import shutil
import subprocess
import yaml

# Đường dẫn file
POLICY_FILE = "policy.yaml"
BACKUP_POLICY = "policy.yaml.bak"

class TestPolicy(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # 1. Backup file policy thật
        if os.path.exists(POLICY_FILE):
            shutil.copy(POLICY_FILE, BACKUP_POLICY)
        
        # 2. Đọc policy thật để lấy roles và permissions
        with open(POLICY_FILE, 'r') as f:
            cls.policy_data = yaml.safe_load(f)
        
        # 3. Lấy tên user hiện tại đang chạy test
        import getpass
        cls.current_user = getpass.getuser()
        
    @classmethod
    def tearDownClass(cls):
        # Restore file policy thật sau khi test xong
        if os.path.exists(BACKUP_POLICY):
            shutil.move(BACKUP_POLICY, POLICY_FILE)

    def create_policy_with_role(self, role):
        """Tạo file policy tạm thời gán user hiện tại vào role mong muốn, GIỮ NGUYÊN roles từ policy thật"""
        # Sử dụng roles từ policy thật
        content = {
            'users': {
                self.current_user: role
            },
            'roles': self.policy_data['roles']
        }
        
        with open(POLICY_FILE, 'w') as f:
            yaml.dump(content, f, default_flow_style=False)

    def test_admin_permission(self):
        """Test: Admin được phép chạy init"""
        self.create_policy_with_role("admin")
        
        # Cleanup trước khi test
        if os.path.exists("store"):
            shutil.rmtree("store")
        
        # Chạy lệnh init (mong đợi thành công - exit code 0)
        result = subprocess.run(
            ["python3", "-m", "src.main", "init", "store"],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, "Admin should be able to init")
        print("\n[PASS] Admin permission test")

    def test_auditor_denial(self):
        """Test: Auditor KHÔNG được phép chạy init"""
        self.create_policy_with_role("auditor")
        
        # Chạy lệnh init (mong đợi thất bại - exit code 1)
        result = subprocess.run(
            ["python3", "-m", "src.main", "init", "store_fail"],
            capture_output=True, text=True
        )
        
        self.assertNotEqual(result.returncode, 0, "Auditor should NOT be able to init")
        self.assertIn("PERMISSION DENIED", result.stdout, "Output should contain denial message")
        print("[PASS] Auditor denial test")
    
    def test_operator_can_backup(self):
        """Test: Operator được phép backup nhưng không được init"""
        self.create_policy_with_role("operator")
        
        # Đảm bảo store đã được init (bởi admin)
        if not os.path.exists("store"):
            # Tạm thời switch sang admin để init
            self.create_policy_with_role("admin")
            subprocess.run(["python3", "-m", "src.main", "init", "store"], 
                         capture_output=True)
            # Switch lại sang operator
            self.create_policy_with_role("operator")
        
        # Tạo test data
        os.makedirs("dataset_operator", exist_ok=True)
        with open("dataset_operator/test.txt", "w") as f:
            f.write("operator test data")
        
        # Test 1: Operator có thể backup
        result = subprocess.run(
            ["python3", "-m", "src.main", "backup", "dataset_operator", "--label", "Op test"],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, "Operator should be able to backup")
        
        # Test 2: Operator KHÔNG thể init
        result = subprocess.run(
            ["python3", "-m", "src.main", "init", "store2"],
            capture_output=True, text=True
        )
        self.assertNotEqual(result.returncode, 0, "Operator should NOT be able to init")
        self.assertIn("PERMISSION DENIED", result.stdout)
        
        # Cleanup
        if os.path.exists("dataset_operator"):
            shutil.rmtree("dataset_operator")
        
        print("[PASS] Operator permission test")

if __name__ == '__main__':
    print("========================================")
    print("=== TEST POLICY ===")
    print("========================================")
    unittest.main()