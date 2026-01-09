# tests/test_policy.py
import unittest
import os
import shutil
import subprocess
import yaml

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

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
        print("\n[TEST 1] Admin Permission Test")
        print(f"User: {self.current_user}, Role: admin")
        self.create_policy_with_role("admin")
        
        # Cleanup trước khi test
        if os.path.exists("store"):
            shutil.rmtree("store")
        
        # Chạy lệnh init (mong đợi thành công - exit code 0)
        print("Running: python3 -m src.main init store")
        result = subprocess.run(
            ["python3", "-m", "src.main", "init", "store"],
            capture_output=True, text=True
        )
        
        print(f"Output: {result.stdout.strip()}")
        if result.stderr:
            print(f"Error: {result.stderr.strip()}")
        print(f"Exit Code: {result.returncode}")
        
        if result.returncode == 0:
            print(f"{GREEN}PASS: Admin có quyền init{NC}")
        else:
            print(f"{RED}FAIL: Admin không thể init (Exit code: {result.returncode}){NC}")
        
        self.assertEqual(result.returncode, 0, "Admin should be able to init")

    def test_auditor_denial(self):
        """Test: Auditor KHÔNG được phép chạy init"""
        print("\n[TEST 2] Auditor Denial Test")
        print(f"User: {self.current_user}, Role: auditor")
        self.create_policy_with_role("auditor")
        
        # Chạy lệnh init (mong đợi thất bại - exit code 1)
        print("Running: python3 -m src.main init store")
        result = subprocess.run(
            ["python3", "-m", "src.main", "init", "store"],
            capture_output=True, text=True
        )
        
        print(f"Output: {result.stdout.strip()}")
        if result.stderr:
            print(f"Error: {result.stderr.strip()}")
        print(f"Exit Code: {result.returncode}")
        
        has_denial = "PERMISSION DENIED" in result.stdout
        if result.returncode != 0 and has_denial:
            print(f"{GREEN}PASS: Auditor bị từ chối init{NC}")
        else:
            print(f"{RED}FAIL: Auditor không bị chặn đúng cách{NC}")
        
        self.assertNotEqual(result.returncode, 0, "Auditor should NOT be able to init")
        self.assertIn("PERMISSION DENIED", result.stdout, "Output should contain denial message")

    def test_operator_can_backup(self):
        """Test: Operator được phép backup nhưng không được init"""
        print("\n[TEST 3] Operator Permission Test")
        print(f"User: {self.current_user}, Role: operator")
        self.create_policy_with_role("operator")
        
        # Đảm bảo store đã được init (bởi admin)
        if not os.path.exists("store"):
            print("Initializing store as admin...")
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
        print("\n[3a] Testing backup permission (should succeed)...")
        print("Running: python3 -m src.main backup dataset_operator --label 'Op test'")
        result = subprocess.run(
            ["python3", "-m", "src.main", "backup", "dataset_operator", "--label", "Op test"],
            capture_output=True, text=True
        )
        print(f"Output: {result.stdout.strip()}")
        print(f"Exit Code: {result.returncode}")
        
        if result.returncode == 0:
            print(f"{GREEN}PASS: Operator có quyền backup{NC}")
        else:
            print(f"{RED}FAIL: Operator không thể backup{NC}")
        
        self.assertEqual(result.returncode, 0, "Operator should be able to backup")
        
        # Test 2: Operator KHÔNG thể init
        print("\n[3b] Testing init denial (should fail)...")
        print("Running: python3 -m src.main init store")
        result = subprocess.run(
            ["python3", "-m", "src.main", "init", "store"],
            capture_output=True, text=True
        )
        print(f"Output: {result.stdout.strip()}")
        print(f"Exit Code: {result.returncode}")
        
        has_denial = "PERMISSION DENIED" in result.stdout
        if result.returncode != 0 and has_denial:
            print(f"{GREEN}PASS: Operator bị từ chối init{NC}")
        else:
            print(f"{RED}FAIL: Operator không bị chặn init{NC}")
        
        self.assertNotEqual(result.returncode, 0, "Operator should NOT be able to init")
        self.assertIn("PERMISSION DENIED", result.stdout)
        
        # Cleanup
        if os.path.exists("dataset_operator"):
            shutil.rmtree("dataset_operator")

if __name__ == '__main__':
    print("=== TEST POLICY ===")
    unittest.main()