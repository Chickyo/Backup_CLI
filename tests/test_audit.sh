#!/bin/bash
# tests/test_audit.sh

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "=== TEST AUDIT LOG INTEGRITY ==="

rm -rf store
mkdir -p dataset_audit

# 1. Tạo một loạt thao tác để ghi log
echo "Generating logs..."
python3 -m src.main init store > /dev/null
python3 -m src.main backup dataset_audit --label "Log 1" > /dev/null
python3 -m src.main list-snapshots > /dev/null

# 2. Kiểm tra Audit sạch
echo "[1] Checking valid audit log..."
OUTPUT=$(python3 -m src.main audit-verify)
echo "$OUTPUT"; 

# 3. Tấn công: Sửa file log
echo "[2] Attacking audit log..."
LOG_FILE="store/audit.log"
# Thay đổi 1 chữ cái trong file log (dùng sed thay thế chữ 'backup' thành 'hacked')
sed -i 's/backup/hacked/' "$LOG_FILE"

# 4. Kiểm tra lại (Phải báo CORRUPTED)
echo "[3] Verifying tampered log..."
OUTPUT=$(python3 -m src.main audit-verify)
echo "$OUTPUT"

if echo "$OUTPUT" | grep -q "AUDIT CORRUPTED"; then
    echo -e "${GREEN}PASS: Phát hiện sửa đổi Audit Log thành công!${NC}"
else
    echo -e "${RED}FAIL: Không phát hiện được sửa đổi trong Log!${NC}"
    exit 1
fi

rm -rf store dataset_audit