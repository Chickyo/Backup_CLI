#!/bin/bash
# tests/test_tamper.sh

# Màu sắc cho đẹp
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=== TEST TAMPERING (Sửa đổi dữ liệu trái phép) ==="

# 1. Setup môi trường
rm -rf store_test_tamper
mkdir -p dataset_test
echo "Original Content" > dataset_test/secret.txt

# 2. Init & Backup
echo "[1] Init và Backup dữ liệu gốc..."
python3 -m src.main init store_test_tamper > /dev/null
python3 -m src.main backup dataset_test --label "Clean Backup" > /dev/null

# Lấy ID snapshot vừa tạo (dòng cuối cùng của list)
SNAP_ID=$(python3 -m src.main list-snapshots | tail -n 1)
echo " -> Snapshot ID: $SNAP_ID"

# 3. Verify lần 1 (Phải OK)
echo "[2] Verify lần đầu (Mong đợi: OK)..."
if python3 -m src.main verify $SNAP_ID; then
    echo -e "${GREEN}PASS: Verify gốc thành công.${NC}"
else
    echo -e "${RED}FAIL: Verify gốc thất bại.${NC}"
    exit 1
fi

# 4. Tấn công: Sửa nội dung 1 Chunk
echo "[3] Tấn công: Sửa đổi 1 byte trong chunk..."
# Tìm file chunk (lấy file đầu tiên tìm thấy trong chunks/)
CHUNK_FILE=$(find store_test_tamper/chunks -type f | head -n 1)
echo " -> Corrupting chunk: $CHUNK_FILE"
echo "HACKED" >> "$CHUNK_FILE"

# 5. Verify lần 2 (Phải FAIL)
echo "[4] Verify sau khi sửa chunk (Mong đợi: FAIL)..."
if ! python3 -m src.main verify $SNAP_ID; then
    echo -e "${GREEN}PASS: Hệ thống đã phát hiện thay đổi chunk!${NC}"
else
    echo -e "${RED}FAIL: Hệ thống không phát hiện ra thay đổi!${NC}"
    exit 1
fi

# Cleanup
rm -rf store_test_tamper dataset_test
echo "=== KẾT THÚC TEST TAMPER ==="