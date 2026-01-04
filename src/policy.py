#Xử lý policy.yaml + Kiểm tra quyền user.
import yaml
import os
import sys

class PolicyManager:
    def __init__(self, policy_path="policy.yaml"):
        self.policy_path = policy_path
        self.users = {}
        self.roles = {}
        self.load_policy()

    def load_policy(self):
        if not os.path.exists(self.policy_path):
            print(f"ERROR: Policy file '{self.policy_path}' not found.")
            sys.exit(1)
        
        with open(self.policy_path, 'r') as f:
            data = yaml.safe_load(f)
            self.users = data.get('users', {})
            self.roles = data.get('roles', {})

    def check_permission(self, user: str, command: str) -> bool:
        """
        Kiểm tra user có quyền chạy lệnh không.
        Trả về True nếu OK, False nếu DENY.
        """
        # 1. Map User -> Role
        role = self.users.get(user)
        if not role:
            # User không có trong policy
            return False

        # 2. Map Role -> Allowed Commands
        allowed_commands = self.roles.get(role, [])
        
        # Admin usually has wildcard or explicitly listed
        if command in allowed_commands:
            return True
        
        return False
        