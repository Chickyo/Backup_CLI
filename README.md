# Backup CLI - Secure Backup System

Hệ thống backup dòng lệnh (CLI) an toàn cho Linux với các tính năng:
- ✅ Toàn vẹn dữ liệu (Data Integrity)
- ✅ Phát hiện chỉnh sửa trái phép (Tamper Detection)
- ✅ Chống rollback (Rollback Protection)
- ✅ An toàn khi crash (Crash Consistency)
- ✅ Kiểm soát truy cập (Access Control)
- ✅ Audit log có thể kiểm tra (Auditable)

---

## 📋 Yêu Cầu Hệ Thống

- **Hệ điều hành:** Linux (Ubuntu, WSL2)
- **Python:** 3.6+
- **Dependencies:** PyYAML

---

## 🚀 Cài Đặt

### 1. Clone repository

```bash
git clone https://github.com/Chickyo/Backup_CLI
cd Backup_CLI
```

### 2. Cài đặt dependencies

```bash
pip3 install -r requirements.txt
```

### 3. Cấu hình Policy (BẮT BUỘC)

⚠️ **QUAN TRỌNG:** File `policy.yaml` nằm ở thư mục gốc của project (cùng cấp với thư mục `src/`). Code sẽ **tự động tìm** file này cho dù bạn chạy lệnh từ thư mục nào.

**Bước 1: Kiểm tra username hiện tại**
```bash
whoami
# Output: ubuntu (hoặc tên user của bạn)
```

**Bước 2: Sửa file policy.yaml**

File `policy.yaml` nằm ở thư mục gốc project. Thêm username của bạn vào phần `users`:

```yaml
users:
  alice: admin
  bob: operator
  eve: auditor
  ubuntu: admin        # ← Thay 'ubuntu' bằng kết quả lệnh whoami
  <your-username>: admin  # ← Hoặc thêm dòng này

roles:
  admin:
    - init
    - backup
    - list-snapshots
    - verify
    - restore
    - audit-verify
  
  operator:
    - backup
    - list-snapshots
    - verify
    - restore
    - audit-verify

  auditor:
    - list-snapshots
    - verify
    - audit-verify
```

**Bước 3: Xác nhận file tồn tại**
```bash
# Kiểm tra file policy.yaml ở thư mục gốc project
ls Backup_CLI/policy.yaml
# Output: Backup_CLI/policy.yaml ✓
```

**Lưu ý:**
- Code tự động tìm file `policy.yaml` ở thư mục gốc project (thư mục cha của `src/`)
- Bạn có thể chạy lệnh CLI từ bất kỳ thư mục nào
- Nếu file không tồn tại hoặc không đọc được → Lỗi: `ERROR: Policy file not found.`

---

## 📁 Cấu Trúc Thư Mục

```
Backup_CLI/
├── src/                    # Source code chính
│   ├── main.py            # Entry point - điều phối CLI
│   ├── audit.py           # Audit log với hash chain
│   ├── integrity.py       # Verify integrity & rollback detection
│   ├── policy.py          # Access control
│   ├── recovery.py        # Crash recovery (WAL)
│   ├── snapshot.py        # Snapshot management
│   ├── storage.py         # Chunking & deduplication
│   └── utils.py           # Utilities (hash, canonical JSON)
│
├── tests/                 # Test scripts
│   ├── run_all_tests.sh   # Chạy tất cả tests
│   ├── test_tamper.sh     # Test phát hiện sửa chunk
│   ├── test_manifest_tamper.sh  # Test phát hiện sửa manifest
│   ├── test_rollback.sh   # Test chống rollback
│   ├── test_audit.sh      # Test audit log integrity
│   ├── test_crash.sh      # Test crash recovery
│   └── test_policy.py     # Test access control
│
├── dataset/               # Dữ liệu mẫu để backup (tự tạo)
├── store/                 # Nơi lưu backup (tự động tạo)
│   ├── chunks/           # Lưu các chunk theo hash
│   ├── snapshots/        # Lưu metadata snapshot
│   ├── journal.log       # Write-Ahead Log
│   └── audit.log         # Audit log
│
├── policy.yaml           # Cấu hình access control
├── requirements.txt      # Python dependencies
└── README.md            
```

---

## 💻 Hướng Dẫn Sử Dụng

⚠️ **Lưu ý:** 
- Code tự động tìm file `policy.yaml` ở thư mục gốc project
- Bạn có thể chạy lệnh từ bất kỳ thư mục nào (không nhất thiết phải ở `Backup_CLI/`)
- Đảm bảo đã cấu hình username trong `policy.yaml`

```bash
# Ví dụ: Chạy từ thư mục gốc
cd Backup_CLI/
python3 -m src.main init store

# Hoặc chạy từ thư mục khác
cd /tmp
python3 -m /path/to/Backup_CLI/src.main init store  # Vẫn hoạt động
```

### 1. Khởi tạo Backup Store

```bash
python3 -m src.main init <store_path>
```

**Ví dụ:**
```bash
python3 -m src.main init store
```

Lệnh này tạo cấu trúc thư mục:
- `store/chunks/` - Lưu trữ các chunk dữ liệu
- `store/snapshots/` - Lưu metadata các snapshot

---

### 2. Tạo Backup (Snapshot)

```bash
python3 -m src.main backup <source_directory> --label "<description>"
```

**Ví dụ:**
```bash
# Tạo dữ liệu mẫu
mkdir -p dataset/images
echo "Important data" > dataset/file.txt
echo "Secret" > dataset/images/photo.jpg

# Backup
python3 -m src.main backup dataset --label "First backup"
```

**Quá trình backup:**
1. Ghi `BEGIN` vào journal.log (WAL)
2. Chia file thành chunks (1MB)
3. Hash mỗi chunk (SHA-256)
4. Lưu chunk vào `store/chunks/<hash>`
5. Tạo manifest.json (mapping file → chunks)
6. Tính Merkle root từ manifest
7. Lưu metadata (id, timestamp, merkle_root, prev_root)
8. Ghi `COMMIT` vào journal.log
9. Ghi vào audit.log

---

### 3. Liệt Kê Snapshots

```bash
python3 -m src.main list-snapshots
```

**Output:**
```
ID              TIMESTAMP
------------------------------
1735948800
1735952400
```

---

### 4. Verify Snapshot

```bash
python3 -m src.main verify <snapshot_id>
```

**Ví dụ:**
```bash
python3 -m src.main verify 1735948800
```

**Kiểm tra:**
- ✅ Tính lại Merkle root từ manifest → so sánh metadata
- ✅ Kiểm tra tất cả chunk tồn tại và đúng hash
- ✅ Kiểm tra chuỗi prev_root (chống rollback)

---

### 5. Restore Snapshot

```bash
python3 -m src.main restore <snapshot_id> <target_directory>
```

**Ví dụ:**
```bash
python3 -m src.main restore 1735948800 restored_data
```

**Lưu ý:** Restore tự động verify trước khi khôi phục.

---

### 6. Verify Audit Log

```bash
python3 -m src.main audit-verify
```

**Kiểm tra:**
- ✅ Hash chain của audit log
- ✅ Mỗi entry có prev_hash trỏ đúng entry trước
- ✅ Entry hash khớp với nội dung

---

## 🧪 Chạy Tests

### Chạy tất cả tests

```bash
bash tests/run_all_tests.sh
```

### Chạy từng test riêng lẻ

```bash
# Test phát hiện sửa chunk
bash tests/test_tamper.sh

# Test phát hiện sửa manifest
bash tests/test_manifest_tamper.sh

# Test chống rollback
bash tests/test_rollback.sh

# Test audit log integrity
bash tests/test_audit.sh

# Test crash recovery
bash tests/test_crash.sh

# Test access control
python3 tests/test_policy.py
```

---

## 🔒 Các Tính Năng Bảo Mật

### 1. **Data Integrity (Toàn vẹn dữ liệu)**

- **Chunking:** File được chia thành chunks 1MB
- **Content-Addressable Storage:** Mỗi chunk lưu theo hash (SHA-256)
- **Merkle Tree:** Manifest được hash thành Merkle root
- **Verify:** So sánh Merkle root và hash từng chunk

**Tấn công bị phát hiện:**
```bash
# Sửa 1 byte trong chunk → verify FAIL
echo "hacked" >> store/chunks/<hash>
python3 -m src.main verify <snapshot_id>  # FAIL
```

---

### 2. **Tamper Detection (Phát hiện sửa đổi)**

- Sửa chunk → hash không khớp
- Sửa manifest.json → Merkle root không khớp
- Sửa metadata.json → Verify fail

---

### 3. **Rollback Protection (Chống rollback)**

- Mỗi snapshot lưu `prev_root` (Merkle root của snapshot trước)
- Verify kiểm tra chuỗi prev_root
- Nếu thay thế snapshot cũ → chain bị đứt → phát hiện

**Ví dụ tấn công:**
```bash
# Xóa snapshot giữa → verify snapshot sau sẽ FAIL
rm -rf store/snapshots/snapshot_<old_id>
python3 -m src.main verify <new_id>  # FAIL: prev_root không khớp
```

---

### 4. **Crash Consistency (An toàn crash)**

- **Write-Ahead Log (WAL):** Ghi `BEGIN` trước, `COMMIT` sau
- **Recovery:** Khi khởi động, scan journal.log
- **Rollback:** Snapshot chưa commit bị xóa tự động

**Giả lập crash:**
```bash
# Giữa quá trình backup, kill process
python3 -m src.main backup dataset --label "Test" &
PID=$!
sleep 1
kill -9 $PID

# Chạy lệnh khác → recovery tự động
python3 -m src.main list-snapshots  # Snapshot lỗi không xuất hiện
```

---

### 5. **Access Control (Kiểm soát truy cập)**

- Dựa trên OS username
- Policy được định nghĩa trong `policy.yaml`
- User không có quyền → lệnh bị từ chối + ghi audit log DENY

**Ví dụ:**
```yaml
users:
  alice: admin
  bob: auditor

roles:
  admin:
    - init
    - backup
    - verify
  auditor:
    - verify
    - list-snapshots
```

```bash
# User bob chạy init → DENY
python3 -m src.main init store  # PERMISSION DENIED
```

---

### 6. **Audit Log (Nhật ký kiểm toán)**

- **Append-only:** Chỉ ghi thêm, không sửa
- **Hash chain:** Mỗi entry chứa hash entry trước
- **Format:**
  ```
  ENTRY_HASH PREV_HASH TIMESTAMP USER COMMAND ARGS_HASH STATUS
  ```

**Verify audit log:**
```bash
python3 -m src.main audit-verify
# Output: AUDIT OK. Head Hash: abc123...
```

**Tấn công bị phát hiện:**
```bash
# Sửa 1 ký tự trong audit.log
sed -i 's/backup/hacked/' store/audit.log
python3 -m src.main audit-verify  # AUDIT CORRUPTED
```

---

## 🎯 Workflow Ví Dụ

### Scenario 1: Backup và Restore

```bash
# 1. Khởi tạo
python3 -m src.main init store

# 2. Tạo dữ liệu
mkdir -p dataset/docs
echo "Project proposal" > dataset/docs/proposal.txt
echo "Budget sheet" > dataset/docs/budget.xlsx

# 3. Backup lần 1
python3 -m src.main backup dataset --label "Initial backup"

# 4. Thay đổi dữ liệu
echo "Updated proposal" > dataset/docs/proposal.txt
rm dataset/docs/budget.xlsx
echo "Timeline" > dataset/docs/timeline.txt

# 5. Backup lần 2
python3 -m src.main backup dataset --label "After updates"

# 6. List snapshots
python3 -m src.main list-snapshots

# 7. Restore về phiên bản cũ
SNAP_ID=$(python3 -m src.main list-snapshots | tail -n 2 | head -n 1)
python3 -m src.main restore $SNAP_ID restored_old

# 8. Kiểm tra
ls restored_old/docs/
# Output: proposal.txt  budget.xlsx (version cũ)
```

---

### Scenario 2: Phát hiện tấn công

```bash
# 1. Tạo backup
python3 -m src.main backup dataset --label "Clean"
SNAP_ID=$(python3 -m src.main list-snapshots | tail -n 1)

# 2. Verify OK
python3 -m src.main verify $SNAP_ID
# Output: VERIFY OK

# 3. Kẻ tấERROR: Policy file 'policy.yaml' not found"

**Nguyên nhân:** File `policy.yaml` bị xóa hoặc không có quyền đọc.

**Giải pháp:**
```bash
# 1. Kiểm tra file có tồn tại không
ls /path/to/Backup_CLI/policy.yaml

# 2. Nếu bị mất, tạo lại
cd /path/to/Backup_CLI
cat > policy.yaml << EOF
users:
  $(whoami): admin

roles:
  admin:
    - init
    - backup
    - list-snapshots
    - verify
    - restore
    - audit-verify
  
  operator:
    - backup
    - list-snapshots: User 'xxx' cannot run 'yyy'"

**Nguyên nhân:** Username của bạn chưa có trong `policy.yaml` hoặc role không có quyền.

**Giải pháp:**
```bash
# 1. Kiểm tra username hiện tại
whoami
# Output: ubuntu

# 2. Mở file policy.yaml
nano policy.yaml

# 3. Thêm user vào (nếu chưa có)
users:
  ubuntu: admin     # ← Thay 'ubuntu' bằng username của bạn

# 4. Hoặc chạy với sudo (username sẽ lấy từ SUDO_USER)

  auditor:
    - list-snapshots
    - verifyl

# Nếu không có, tạo mới
cat > policy.yaml << EOF
users:
  $(whoami): admin

roles:
  admin:
    - init
    - backup
    - list-snapshots
    - verify
    - restore
    - audit-verify
EOF
```

### Lỗi: "PERMISSION DENIED"
```bash
# Thêm user vào policy.yaml
# hoặc chạy với sudo
sudo python3 -m src.main <command>
```

### Lỗi: "Store not found"
```bash
# Đảm bảo đã init store trước
python3 -m src.main init store
```

---

## 📚 Thiết Kế Kỹ Thuật

### Snapshot Structure
```
store/snapshots/snapshot_<id>/
├── manifest.json       # { "file1.txt": ["chunk_hash1", "chunk_hash2"], ... }
└── metadata.json       # { id, timestamp, label, merkle_root, prev_root }
```

### Chunk Storage
```
store/chunks/
└── <sha256_hash>      # Binary content của chunk
```

### Journal Log (WAL)
```
BEGIN 1735948800
COMMIT 1735948800
BEGIN 1735952400
COMMIT 1735952400
```

### Audit Log
```
entry_hash prev_hash timestamp user command args_hash status
abc123...  000000... 1735948800000 alice init d41d8c... OK
def456...  abc123... 1735949000000 alice backup 9e107d... OK
```