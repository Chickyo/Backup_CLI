#!/bin/bash
# tests/test_crash.sh

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "=== TEST CRASH RECOVERY (JOURNAL) ==="

rm -rf store
python3 -m src.main init store > /dev/null

# 1. Giả lập Crash
# Tạo thủ công một thư mục snapshot rác
FAKE_ID="9999999999"
mkdir -p store/snapshots/snapshot_$FAKE_ID
echo "Garbage Data" > store/snapshots/snapshot_$FAKE_ID/manifest.json

# Ghi vào Journal: BEGIN nhưng KHÔNG CÓ COMMIT
echo "BEGIN $FAKE_ID" >> store/journal.log

echo "-> Đã tạo giả lập crash: Snapshot $FAKE_ID chưa commit."

# 2. Chạy một lệnh bất kỳ để kích hoạt Recovery
echo "Running list-snapshots to trigger recovery..."
python3 -m src.main list-snapshots > /dev/null

# 3. Kiểm tra xem snapshot rác đã bị xoá chưa
if [ ! -d "store/snapshots/snapshot_$FAKE_ID" ]; then
    echo -e "${GREEN}PASS: Crash Recovery hoạt động tốt (Snapshot lỗi đã bị xoá).${NC}"
else
    echo -e "${RED}FAIL: Snapshot lỗi vẫn còn tồn tại!${NC}"
    exit 1
fi