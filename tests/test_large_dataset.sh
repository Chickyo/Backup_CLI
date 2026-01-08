#!/bin/bash
# tests/test_large_dataset.sh
# Test: Backup và verify với 2000 files

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

echo "=== TEST LARGE DATASET (2000 files) ==="

# 1. Setup
rm -rf store_large dataset_large
mkdir -p dataset_large

# 2. Tạo 2000 files với cấu trúc thư mục phân cấp
echo "[1] Tạo 2000 files..."
for i in {1..2000}; do
    # Tạo cấu trúc thư mục: dir_0 đến dir_19 (mỗi dir có 100 files)
    dir_num=$((i / 100))
    mkdir -p dataset_large/dir_$dir_num
    
    # Tạo file với nội dung ngẫu nhiên
    file_path="dataset_large/dir_$dir_num/file_$i.txt"
    
    # Sinh dữ liệu: timestamp + random string + số thứ tự
    echo "File #$i - Created at $(date +%s)" > "$file_path"
    echo "Random data: $(openssl rand -base64 32)" >> "$file_path"
    echo "Content line 1: Lorem ipsum dolor sit amet $i" >> "$file_path"
    echo "Content line 2: consectetur adipiscing elit $i" >> "$file_path"
    
    # Progress indicator mỗi 200 files
    if [ $((i % 200)) -eq 0 ]; then
        echo "   Created $i files..."
    fi
done

echo "✓ Created 2000 files in 20 directories"

# 3. Tính tổng kích thước
TOTAL_SIZE=$(du -sh dataset_large | cut -f1)
echo "   Total dataset size: $TOTAL_SIZE"

# 4. Init và Backup
echo "[2] Initializing store and creating backup..."
python3 -m src.main init store_large > /dev/null

START_TIME=$(date +%s)
python3 -m src.main backup dataset_large --label "Large Dataset Test" --store store_large

END_TIME=$(date +%s)
BACKUP_TIME=$((END_TIME - START_TIME))
echo "   Backup completed in $BACKUP_TIME seconds"

# 5. Lấy Snapshot ID
SNAP_ID=$(python3 -m src.main list-snapshots --store store_large | tail -n 1)
echo "   Snapshot ID: $SNAP_ID"

# 6. Verify integrity
echo "[3] Verifying snapshot integrity..."
START_TIME=$(date +%s)
if python3 -m src.main verify $SNAP_ID --store store_large; then
    END_TIME=$(date +%s)
    VERIFY_TIME=$((END_TIME - START_TIME))
    echo -e "${GREEN}PASS: Verify completed in $VERIFY_TIME seconds${NC}"
else
    echo -e "${RED}FAIL: Verify failed${NC}"
    exit 1
fi

# 7. Thống kê
echo ""
echo "=== STATISTICS ==="
echo "Total files: 2000"
echo "Total directories: 20"
echo "Dataset size: $TOTAL_SIZE"
echo "Backup time: $BACKUP_TIME seconds"
echo "Verify time: $VERIFY_TIME seconds"
echo "Chunks created: $(ls -1 store_large/chunks | wc -l)"
echo "Store size: $(du -sh store_large | cut -f1)"

# Cleanup
echo ""
read -p "Keep dataset and store? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    rm -rf store_large dataset_large
    echo "Cleaned up."
else
    echo "Dataset and store preserved in dataset_large/ and store_large/"
fi

echo "=== TEST COMPLETED ==="
