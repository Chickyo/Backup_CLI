#!/bin/bash
# tests/test_rollback.sh

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "=== TEST ROLLBACK PROTECTION ==="

# Setup môi trường
rm -rf store dataset_rollback
mkdir -p dataset_rollback

# 1. Tạo Snapshot cũ (Old)
echo "Old Data" > dataset_rollback/file.txt
python3 -m src.main init store > /dev/null
python3 -m src.main backup dataset_rollback --label "Old Snapshot" > /dev/null
SNAP_OLD=$(python3 -m src.main list-snapshots | tail -n 1)
echo " -> Created Old Snapshot: $SNAP_OLD"

# Backup snapshot cũ
cp -r "store/snapshots/snapshot_$SNAP_OLD" "store/snapshots/snapshot_${SNAP_OLD}_backup"

sleep 1 # Đợi 1s để timestamp khác nhau

# 2. Tạo Snapshot mới (New)
echo "New Data - Updated" > dataset_rollback/file.txt
python3 -m src.main backup dataset_rollback --label "New Snapshot" > /dev/null
SNAP_NEW=$(python3 -m src.main list-snapshots | tail -n 1)
echo " -> Created New Snapshot: $SNAP_NEW"

# 3. Verify snapshot mới (Phải OK)
echo ""
echo "[Before Attack] Verify snapshot mới - Mong đợi: OK..."
python3 -m src.main verify $SNAP_NEW

# 4. Tấn công: ROLLBACK - Thay thế snapshot mới bằng snapshot cũ
echo ""
echo "[ROLLBACK ATTACK] Thay thế snapshot mới ($SNAP_NEW) bằng snapshot cũ ($SNAP_OLD)..."

rm -rf "store/snapshots/snapshot_$SNAP_NEW"
cp -r "store/snapshots/snapshot_${SNAP_OLD}_backup" "store/snapshots/snapshot_$SNAP_NEW"

# 5. Verify snapshot sau khi rollback (Phải FAIL)
echo ""
echo "[After Attack] Verify snapshot $SNAP_NEW - Mong đợi: FAIL (rollback detected)..."
OUTPUT=$(python3 -m src.main verify $SNAP_NEW 2>&1)
echo "$OUTPUT"

# 6. Kiểm tra kết quả
echo ""
if echo "$OUTPUT" | grep -q "VERIFY FAIL"; then
    echo -e "${GREEN}PASS: Hệ thống phát hiện được ROLLBACK ATTACK!${NC}"
else
    echo -e "${RED}FAIL: Không phát hiện được rollback attack${NC}"
fi

echo ""
echo "=== KẾT THÚC TEST ROLLBACK ==="