#!/bin/bash
# tests/test_rollback.sh

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "=== TEST ROLLBACK PROTECTION ==="

# Setup môi trường
rm -rf store dataset_rollback
mkdir -p dataset_rollback

# 1. Tạo Snapshot 1
echo "Data 1" > dataset_rollback/file.txt
python3 -m src.main init store > /dev/null
python3 -m src.main backup dataset_rollback --label "Snap 1" > /dev/null
SNAP1=$(python3 -m src.main list-snapshots | tail -n 1)
sleep 1 # Đợi 1s để timestamp khác nhau

# 2. Tạo Snapshot 2
echo "Data 2" > dataset_rollback/file.txt
python3 -m src.main backup dataset_rollback --label "Snap 2" > /dev/null
SNAP2=$(python3 -m src.main list-snapshots | tail -n 1)

echo " -> Created Snap 1: $SNAP1"
echo " -> Created Snap 2: $SNAP2"

# 3. Tấn công: Sửa prev_root của Snap 2
# Giả lập kẻ tấn công cố tình trỏ prev_root của Snap 2 về 0 (như thể nó là snap đầu tiên)
# hoặc sửa thành hash rác.
echo "[Attack] Sửa đổi metadata của Snapshot 2 (phá vỡ chain)..."
META_PATH="store/snapshots/snapshot_$SNAP2/metadata.json"

# Thay prev_root thật bằng một chuỗi fake
sed -i 's/"prev_root":"[a-f0-9]*"/"prev_root":"deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"/' "$META_PATH"

# 4. Verify Snap 2 (Phải FAIL do lệch prev_root với root của Snap 1)
echo "Running Verify..."
python3 -m src.main verify $SNAP2;