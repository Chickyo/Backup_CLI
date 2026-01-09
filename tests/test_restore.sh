#!/bin/bash
# tests/test_restore.sh
# Test restore: xóa files, restore từ snapshot, và so sánh kết quả

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================"
echo "=== TEST RESTORE & COMPARE PROJECT ==="
echo "========================================"

rm -rf dataset_test_original dataset_test_restored
rm -f /tmp/checksums_original.txt /tmp/checksums_restored.txt

# 1. Kiểm tra dataset_test có tồn tại không
if [ ! -d "dataset_test" ]; then
    echo -e "${YELLOW}WARNING: dataset_test not found. Running generate_dataset.sh...${NC}"
    
    # Chạy lệnh tạo dataset
    bash tests/generate_dataset.sh
    
    # Kiểm tra lại xem sau khi chạy script thì dataset đã được tạo chưa
    if [ ! -d "dataset_test" ]; then
        echo -e "${RED}ERROR: Failed to create dataset_test. Exiting...${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}SUCCESS: dataset_test created successfully.${NC}"
fi

# 2. Init và Backup
echo "[1] Creating backup of dataset_test..."
rm -rf store
python3 -m src.main init store > /dev/null
python3 -m src.main backup dataset_test --label "Full Backup 2000 files"

# Làm sạch ID snapshot để tránh lỗi ký tự xuống dòng
SNAP_ID=$(python3 -m src.main list-snapshots | tail -n 1 | awk '{print $1}' | tr -d '\r\n ')
echo " -> Snapshot ID: $SNAP_ID"

# 3. Tạo bản sao để so sánh sau này
echo "[2] Creating backup copy for comparison..."
rm -rf dataset_test_original
cp -r dataset_test dataset_test_original

# 4. Đếm số files và tính checksum
ORIGINAL_COUNT=$(find dataset_test_original -type f | wc -l)
echo " -> Original file count: $ORIGINAL_COUNT"

echo "[3] Computing checksums of original files..."
(cd dataset_test_original && find . -type f -exec sha256sum {} \;) | sort > /tmp/checksums_original.txt

# 5. Xóa một số files từ dataset_test (xóa 30% files) và xóa 5 thư mục đầu tiên
echo "[4] Deleting 30% of files from dataset_test..."
FILES_TO_DELETE=$((ORIGINAL_COUNT * 30 / 100))
find dataset_test -type f | shuf | head -n $FILES_TO_DELETE | while read file; do
    rm -f "$file"
done

echo " -> Deleting first 5 directories..."
find dataset_test -mindepth 1 -type d | head -n 5 | while read dir; do
    echo "    Removing: $dir"
    rm -rf "$dir"
done

AFTER_DELETE_COUNT=$(find dataset_test -type f | wc -l)
echo " -> Files after deletion: $AFTER_DELETE_COUNT (deleted: $((ORIGINAL_COUNT - AFTER_DELETE_COUNT)))"

# 6. Restore từ snapshot
echo "[5] Restoring from snapshot $SNAP_ID..."
rm -rf dataset_test_restored
python3 -m src.main restore $SNAP_ID dataset_test_restored

# 7. Kiểm tra số lượng files sau restore
RESTORED_COUNT=$(find dataset_test_restored -type f | wc -l)
echo " -> Restored file count: $RESTORED_COUNT"

if [ "$RESTORED_COUNT" -ne "$ORIGINAL_COUNT" ]; then
    echo -e "${RED}FAIL: File count mismatch! Original: $ORIGINAL_COUNT, Restored: $RESTORED_COUNT${NC}"
    exit 1
else
    echo -e "${GREEN}PASS: File count matches ($RESTORED_COUNT)${NC}"
fi

# 8. So sánh cây thư mục
echo "[6] Comparing directory structure..."
TREE_DIFF=$(diff <(cd dataset_test_original && find . -type d | sort) <(cd dataset_test_restored && find . -type d | sort))
if [ -z "$TREE_DIFF" ]; then
    echo -e "${GREEN}PASS: Directory structure identical${NC}"
else
    echo -e "${RED}FAIL: Directory structure differs:${NC}"
    echo "$TREE_DIFF"
    exit 1
fi

# 9. So sánh checksum của tất cả files
echo "[7] Comparing file contents (checksum)..."
# QUAN TRỌNG: cd vào trong thư mục restored để so sánh tương ứng với original
(cd dataset_test_restored && find . -type f -exec sha256sum {} \;) | sort > /tmp/checksums_restored.txt

CHECKSUM_DIFF=$(diff /tmp/checksums_original.txt /tmp/checksums_restored.txt)
if [ -z "$CHECKSUM_DIFF" ]; then
    echo -e "${GREEN}PASS: All file contents match (checksums identical)${NC}"
else
    echo -e "${RED}FAIL: File contents differ!${NC}"
    echo "--- First 10 differences ---"
    echo "$CHECKSUM_DIFF" | head -n 10
    exit 1
fi

# 10. So sánh chi tiết bằng diff -r
echo "[8] Deep comparison with diff -r..."
if diff -r dataset_test_original dataset_test_restored > /dev/null 2>&1; then
    echo -e "${GREEN}PASS: Deep comparison successful - all files identical${NC}"
else
    # Một số trường hợp diff -r fail do khác metadata dù nội dung giống, 
    # nhưng với bài LAB này thường là do nội dung file.
    echo -e "${RED}FAIL: Deep comparison found differences (check permissions or timestamps)${NC}"
    exit 1
fi

# Cleanup với xác nhận Yes/No
echo ""
echo "=== CLEANUP SECTION ==="
read -p "Bạn có muốn xóa các thư mục tạm và file checksum không? (y/n): " confirm

if [[ "$confirm" == "y" || "$confirm" == "Y" ]]; then
    echo "Đang tiến hành dọn dẹp..."
    rm -rf dataset_test_original dataset_test_restored
    rm -f /tmp/checksums_original.txt /tmp/checksums_restored.txt
    echo -e "${GREEN}Dọn dẹp hoàn tất.${NC}"
else
    echo -e "${YELLOW}Đã giữ lại các thư mục để bạn kiểm tra thủ công.${NC}"
fi
