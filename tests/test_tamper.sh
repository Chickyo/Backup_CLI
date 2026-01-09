#!/bin/bash
# tests/test_tamper.sh

echo "=== TEST TAMPERING (Sửa đổi dữ liệu trái phép) ==="

# 1. Setup môi trường
rm -rf store dataset_test
mkdir -p dataset_test
echo "Original Content" > dataset_test/secret.txt

# 2. Init & Backup
echo "[1] Init và Backup dữ liệu gốc..."
python3 -m src.main init store > /dev/null
python3 -m src.main backup dataset_test --label "Clean Backup" > /dev/null

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
python3 -m src.main verify $SNAP_ID;

# Cleanup
# rm -rf store dataset_test
echo "=== KẾT THÚC TEST TAMPER ==="