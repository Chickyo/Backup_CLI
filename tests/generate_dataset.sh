#!/bin/bash
# tests/generate_dataset.sh
# Script sinh 2000 files với dữ liệu ngẫu nhiên vào dataset_test

echo "=== GENERATING 2000 FILES IN dataset_test ==="

# Xóa thư mục cũ nếu tồn tại
rm -rf dataset_test
mkdir -p dataset_test

# Tạo cấu trúc thư mục con
for i in {1..10}; do
    mkdir -p dataset_test/folder_$i
done

# Sinh 2000 files
echo "Generating files..."
for i in {1..2000}; do
    # Xác định thư mục (phân bố đều vào 10 folder + root)
    if [ $((i % 11)) -eq 0 ]; then
        DIR="dataset_test"
    else
        FOLDER_NUM=$((i % 10 + 1))
        DIR="dataset_test/folder_$FOLDER_NUM"
    fi
    
    # Tạo file với nội dung ngẫu nhiên
    FILE="$DIR/file_$(printf "%04d" $i).txt"
    
    # Sinh nội dung: timestamp, số ngẫu nhiên, và text
    echo "File ID: $i" > "$FILE"
    echo "Created: $(date)" >> "$FILE"
    echo "Random: $RANDOM$RANDOM$RANDOM" >> "$FILE"
    echo "Content: Lorem ipsum dolor sit amet, consectetur adipiscing elit." >> "$FILE"
    echo "Data line: $(head -c 100 /dev/urandom | base64 | head -c 100)" >> "$FILE"
    
    # Hiển thị tiến trình mỗi 200 files
    if [ $((i % 200)) -eq 0 ]; then
        echo "  -> Created $i files..."
    fi
done

# Thống kê
TOTAL_FILES=$(find dataset_test -type f | wc -l)
TOTAL_SIZE=$(du -sh dataset_test | cut -f1)

echo "=== GENERATION COMPLETE ==="
echo "Total files: $TOTAL_FILES"
echo "Total size: $TOTAL_SIZE"
