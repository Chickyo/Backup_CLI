#!/bin/bash
# tests/test_tamper.sh

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'


echo "=== TEST TAMPERING ==="

# 1. Setup môi trường
rm -rf store dataset_tamper
mkdir -p dataset_tamper
echo "Original Content" > dataset_tamper/secret.txt

# 2. Init & Backup
echo "[1] Init và Backup dữ liệu gốc..."
python3 -m src.main init store > /dev/null
python3 -m src.main backup dataset_tamper --label "Clean Backup" > /dev/null

# Lấy ID snapshot vừa tạo (dòng cuối cùng của list)
SNAP_ID=$(python3 -m src.main list-snapshots | tail -n 1)
echo " -> Snapshot ID: $SNAP_ID"

# 3. Verify lần 1 (Phải OK)
echo "[2] Verify lần đầu (Mong đợi: OK)..."
python3 -m src.main verify $SNAP_ID;

# 4. Tấn công: Sửa nội dung 1 Chunk
echo "[3] Tấn công: Sửa đổi 1 byte trong chunk..."
# Tìm file chunk (lấy file đầu tiên tìm thấy trong chunks/)
CHUNK_FILE=$(find store/chunks -type f | head -n 1)
echo " -> Corrupting chunk: $CHUNK_FILE"
echo "HACKED" >> "$CHUNK_FILE"

# 5. Verify lần 2 (Phải FAIL)
echo "[4] Verify sau khi sửa chunk (Mong đợi: FAIL)..."
OUTPUT=$(python3 -m src.main verify $SNAP_ID);

# 6. Kiểm tra kết quả
echo "$OUTPUT"
if echo "$OUTPUT" | grep -q "VERIFY FAIL"; then
    echo -e "${GREEN}PASS: Hệ thống phát hiện được sửa đổi chunk!${NC}"
else
    echo -e "${RED}FAIL: Không phát hiện được sửa đổi chunk${NC}"
fi

# Cleanup
# rm -rf store dataset_tamper
echo "=== KẾT THÚC TEST TAMPER ==="