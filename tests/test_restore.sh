#!/bin/bash
# tests/test_restore.sh
# Test: Xóa files từ source, restore từ snapshot và so sánh

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

echo "=== TEST RESTORE & COMPARE ==="

# 1. Setup - Tạo dataset gốc
rm -rf store_restore dataset_original dataset_backup restored_data
mkdir -p dataset_original

echo "[1] Tạo dataset gốc với cấu trúc phức tạp..."

# Tạo cấu trúc thư mục phân cấp
mkdir -p dataset_original/documents/reports
mkdir -p dataset_original/documents/memos
mkdir -p dataset_original/images/photos
mkdir -p dataset_original/images/screenshots
mkdir -p dataset_original/code/python
mkdir -p dataset_original/code/java
mkdir -p dataset_original/data

# Tạo files với nội dung đa dạng
echo "Annual Report 2025" > dataset_original/documents/reports/annual_2025.txt
echo "Q4 Financial Data" > dataset_original/documents/reports/q4_finance.txt
for i in {1..10}; do
    echo "Memo #$i - $(date +%Y-%m-%d)" > dataset_original/documents/memos/memo_$i.txt
done

# Images (binary-like data)
for i in {1..5}; do
    dd if=/dev/urandom of=dataset_original/images/photos/photo_$i.jpg bs=1024 count=10 2>/dev/null
    dd if=/dev/urandom of=dataset_original/images/screenshots/screen_$i.png bs=512 count=5 2>/dev/null
done

# Code files
cat > dataset_original/code/python/main.py << 'EOF'
def main():
    print("Hello World")
    return 0

if __name__ == "__main__":
    main()
EOF

cat > dataset_original/code/python/utils.py << 'EOF'
def calculate(a, b):
    return a + b

def process_data(data):
    return [x * 2 for x in data]
EOF

cat > dataset_original/code/java/Main.java << 'EOF'
public class Main {
    public static void main(String[] args) {
        System.out.println("Hello Java");
    }
}
EOF

# Data files
for i in {1..20}; do
    echo "Data record #$i: $(openssl rand -hex 16)" > dataset_original/data/record_$i.csv
done

echo "✓ Created original dataset"
TOTAL_FILES=$(find dataset_original -type f | wc -l)
echo "   Total files: $TOTAL_FILES"
echo "   Total size: $(du -sh dataset_original | cut -f1)"

# 2. Tạo backup của dataset gốc (để so sánh sau này)
echo "[2] Tạo bản sao dataset gốc..."
cp -r dataset_original dataset_backup

# 3. Init và Backup
echo "[3] Backup dataset..."
python3 -m src.main init store_restore > /dev/null
python3 -m src.main backup dataset_original --label "Original Dataset" --store store_restore

SNAP_ID=$(python3 -m src.main list-snapshots --store store_restore | tail -n 1)
echo "   Snapshot ID: $SNAP_ID"

# 4. Verify backup
echo "[4] Verifying backup..."
if ! python3 -m src.main verify $SNAP_ID --store store_restore; then
    echo -e "${RED}FAIL: Backup verification failed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Backup verified${NC}"

# 5. Xóa một số files và thư mục từ dataset gốc
echo "[5] Xóa một số files từ dataset gốc..."
rm -rf dataset_original/documents/memos
rm -f dataset_original/documents/reports/q4_finance.txt
rm -rf dataset_original/images/photos
rm -f dataset_original/code/python/utils.py
rm -f dataset_original/data/record_{1..10}.csv

REMAINING_FILES=$(find dataset_original -type f 2>/dev/null | wc -l)
echo "   Files remaining: $REMAINING_FILES (deleted $((TOTAL_FILES - REMAINING_FILES)) files)"

# 6. Restore từ snapshot
echo "[6] Restoring từ snapshot..."
python3 -m src.main restore $SNAP_ID restored_data --store store_restore

if [ ! -d "restored_data" ]; then
    echo -e "${RED}FAIL: Restore failed - directory not created${NC}"
    exit 1
fi

RESTORED_FILES=$(find restored_data -type f | wc -l)
echo "   Files restored: $RESTORED_FILES"

# 7. So sánh cây thư mục
echo ""
echo "=== COMPARING DIRECTORY STRUCTURE ==="

echo "[7.1] Comparing directory tree..."
TREE_BACKUP=$(cd dataset_backup && find . -type d | sort)
TREE_RESTORED=$(cd restored_data && find . -type d | sort)

if [ "$TREE_BACKUP" = "$TREE_RESTORED" ]; then
    echo -e "${GREEN}✓ PASS: Directory structure matches${NC}"
else
    echo -e "${RED}✗ FAIL: Directory structure mismatch${NC}"
    echo "Expected directories:"
    echo "$TREE_BACKUP"
    echo ""
    echo "Restored directories:"
    echo "$TREE_RESTORED"
    exit 1
fi

# 8. So sánh số lượng files
echo "[7.2] Comparing file count..."
BACKUP_COUNT=$(find dataset_backup -type f | wc -l)
RESTORED_COUNT=$(find restored_data -type f | wc -l)

if [ $BACKUP_COUNT -eq $RESTORED_COUNT ]; then
    echo -e "${GREEN}✓ PASS: File count matches ($BACKUP_COUNT files)${NC}"
else
    echo -e "${RED}✗ FAIL: File count mismatch${NC}"
    echo "   Expected: $BACKUP_COUNT"
    echo "   Restored: $RESTORED_COUNT"
    exit 1
fi

# 9. So sánh nội dung từng file
echo "[7.3] Comparing file contents..."
MISMATCH_COUNT=0
COMPARED_COUNT=0

while IFS= read -r file; do
    rel_path=${file#./}
    COMPARED_COUNT=$((COMPARED_COUNT + 1))
    
    if [ ! -f "restored_data/$rel_path" ]; then
        echo -e "${RED}✗ Missing file: $rel_path${NC}"
        MISMATCH_COUNT=$((MISMATCH_COUNT + 1))
        continue
    fi
    
    # So sánh nội dung bằng diff
    if ! diff -q "dataset_backup/$rel_path" "restored_data/$rel_path" > /dev/null 2>&1; then
        echo -e "${RED}✗ Content mismatch: $rel_path${NC}"
        MISMATCH_COUNT=$((MISMATCH_COUNT + 1))
    fi
    
    # Progress indicator
    if [ $((COMPARED_COUNT % 10)) -eq 0 ]; then
        echo -n "."
    fi
done < <(cd dataset_backup && find . -type f | sort)

echo ""

if [ $MISMATCH_COUNT -eq 0 ]; then
    echo -e "${GREEN}✓ PASS: All $COMPARED_COUNT files match exactly${NC}"
else
    echo -e "${RED}✗ FAIL: $MISMATCH_COUNT out of $COMPARED_COUNT files mismatch${NC}"
    exit 1
fi

# 10. So sánh kích thước tổng thể
echo "[7.4] Comparing total size..."
BACKUP_SIZE=$(du -sb dataset_backup | cut -f1)
RESTORED_SIZE=$(du -sb restored_data | cut -f1)

if [ $BACKUP_SIZE -eq $RESTORED_SIZE ]; then
    HUMAN_SIZE=$(du -sh dataset_backup | cut -f1)
    echo -e "${GREEN}✓ PASS: Total size matches ($HUMAN_SIZE)${NC}"
else
    echo -e "${RED}✗ FAIL: Size mismatch${NC}"
    echo "   Expected: $BACKUP_SIZE bytes"
    echo "   Restored: $RESTORED_SIZE bytes"
    exit 1
fi

# 11. Tổng kết
echo ""
echo "=== SUMMARY ==="
echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
echo "   Directory structure: ✓"
echo "   File count: ✓ ($BACKUP_COUNT files)"
echo "   File contents: ✓ (all files identical)"
echo "   Total size: ✓ ($HUMAN_SIZE)"
echo ""
echo "Restore operation successfully recovered all data!"

# Cleanup
rm -rf store_restore dataset_original dataset_backup restored_data

echo "=== TEST COMPLETED ==="
