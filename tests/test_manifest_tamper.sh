#!/bin/bash
# tests/test_manifest_tamper.sh
# Test: Sửa manifest.json → verify fail

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "=== TEST MANIFEST TAMPERING ==="
# 1. Setup
# Cleanup
rm -rf store dataset_manifest

mkdir -p dataset_manifest
echo "Test Data" > dataset_manifest/file.txt

# 2. Init & Backup
echo "[1] Creating backup..."
python3 -m src.main init store > /dev/null
python3 -m src.main backup dataset_manifest --label "Test" > /dev/null

# Get snapshot ID
SNAP_ID=$(python3 -m src.main list-snapshots | tail -n 1)
echo " -> Snapshot ID: $SNAP_ID"

# 3. Verify original (should pass)
echo "[2] Verifying original snapshot..."
python3 -m src.main verify $SNAP_ID; 

# 4. Tamper manifest.json
echo "[3] Tampering with manifest.json..."
MANIFEST_FILE="store/snapshots/snapshot_$SNAP_ID/manifest.json"
# Thay đổi nội dung manifest bằng cách thêm 1 ký tự
echo "}" >> "$MANIFEST_FILE"

# 5. Verify after tampering (should fail)
echo "[4] Verifying tampered snapshot..."
OUTPUT=$(python3 -m src.main verify $SNAP_ID);
echo "$OUTPUT"
if echo "$OUTPUT" | grep -q "VERIFY FAIL"; then
    echo -e "${GREEN}PASS: Hệ thống phát hiện được sửa đổi manifest!${NC}"
else
    echo -e "${RED}FAIL: Không phát hiện được sửa đổi manifest${NC}"
    exit 1
fi

echo "=== MANIFEST TAMPER TEST COMPLETED ==="
