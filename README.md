# Backup CLI – Hệ thống sao lưu đảm bảo toàn vẹn dữ liệu

## 1. Giới thiệu

Backup CLI là công cụ sao lưu dòng lệnh phục vụ mục tiêu bảo vệ toàn vẹn dữ liệu và khả năng kiểm chứng.
Hệ thống tập trung phát hiện các hành vi tấn công phổ biến trên hệ thống backup như:

- Sửa dữ liệu đã sao lưu (chunk tampering)
- Sửa manifest / metadata
- Rollback snapshot
- Sửa hoặc xoá audit log
- Crash giữa quá trình backup

Hệ thống không mã hóa dữ liệu, không nhắm tới bảo mật nội dung, mà tập trung vào integrity, auditability và crash recovery.

## 2. Cài đặt và chạy chương trình

### 2.1. Yêu cầu môi trường

- Hệ điều hành: Linux (khuyến nghị WSL2)
- Python: 3.10 trở lên
- Không sử dụng thư viện ngoài chuẩn Python

### 2.2. Cấu trúc thư mục chính

```text
.
├── src/
│   └── main.py
├── store/
│   ├── chunks/
│   ├── snapshots/
│   ├── roots.log
│   ├── audit.log
│   └── journal.log
├── policy.yaml
├── tests/
└── README.md
```

### 2.3. Các lệnh cơ bản

```bash
python3 -m src.main init store
python3 -m src.main backup <source_dir> --label "My Backup"
python3 -m src.main list-snapshots
python3 -m src.main verify <snapshot_id>
python3 -m src.main restore <snapshot_id> <output_dir>
python3 -m src.main audit-verify
```

## 3. Chunk size, Canonical Manifest và Merkle Root

### 3.1. Chunking

- Kích thước chunk cố định: 1 MiB
- Mỗi chunk được hash bằng SHA-256
- Chunk được lưu tại: `store/chunks/<chunk_hash>`
- Deduplication được thực hiện tự nhiên thông qua hash: các chunk trùng nội dung chỉ lưu một lần.

### 3.2. Canonical Manifest

Mỗi snapshot chứa file manifest.json, ánh xạ đường dẫn file tương đối tới danh sách các chunk hash:

```json
{
  "path/to/file.txt": [
    "chunk_hash_1",
    "chunk_hash_2"
  ]
}
```

Manifest được ghi dưới dạng canonical JSON:

- Key được sort
- Không thừa khoảng trắng
- Serialize ổn định

Điều này đảm bảo rằng cùng một nội dung dữ liệu sẽ luôn tạo ra cùng một hash, không phụ thuộc thứ tự duyệt file.

### 3.3. Tính Merkle Root

Merkle root được tính từ toàn bộ nội dung manifest.json và được lưu trong metadata.json:

```json
{
  "id": "<snapshot_id>",
  "timestamp": 1234567890.0,
  "label": "Backup name",
  "merkle_root": "<hex>",
  "prev_root": "<hex>"
}
```

Khi verify snapshot:

- Đọc manifest và metadata
- Tính lại Merkle root từ manifest
- So sánh với metadata.merkle_root
- Hash lại từng chunk để phát hiện sửa đổi dữ liệu

## 4. Cơ chế chống rollback snapshot

### 4.1. Nguyên lý

- Mỗi snapshot lưu prev_root
- File roots.log là một hash chain, mỗi dòng có dạng: `ENTRY_HASH PREV_HASH ROOT`
- Trong đó: `ENTRY_HASH = H(PREV_HASH || ROOT)`
- Bất kỳ thao tác xóa, chèn hoặc thay đổi thứ tự snapshot đều làm đứt hash chain và bị phát hiện khi verify.

### 4.2. Reproduce test rollback

```bash
# Init store
python3 -m src.main init store

# Tạo snapshot cũ
echo "Data 1" > file.txt
python3 -m src.main backup . --label "Old Snapshot"
SNAP_OLD=$(python3 -m src.main list-snapshots | tail -n 1)

# Tạo snapshot mới
sleep 1
echo "Data 2" > file.txt
python3 -m src.main backup . --label "New Snapshot"
SNAP_NEW=$(python3 -m src.main list-snapshots | tail -n 1)

# Tấn công rollback
rm -rf store/snapshots/snapshot_$SNAP_NEW/*
cp -r store/snapshots/snapshot_$SNAP_OLD/* store/snapshots/snapshot_$SNAP_NEW/

# Verify
python3 -m src.main verify $SNAP_NEW
```

Kết quả mong đợi: VERIFY FAIL – rollback detected.

## 5. Journal / WAL và phục hồi crash

### 5.1. Journal (Write-Ahead Log)

File journal.log ghi nhận trạng thái backup:

- BEGIN <snapshot_id>
- COMMIT <snapshot_id>

Luồng backup an toàn:

- Ghi BEGIN
- Ghi chunk, manifest, metadata
- Append roots.log
- Ghi COMMIT

### 5.2. Phục hồi crash

Khi chương trình khởi động:

- Quét journal.log
- Snapshot nào có BEGIN nhưng không có COMMIT sẽ bị xem là snapshot dở và bị xoá

Reproduce crash test:

```bash
echo "BEGIN 9999999999" >> store/journal.log
mkdir store/snapshots/snapshot_9999999999
python3 -m src.main list-snapshots
```

Snapshot giả sẽ bị cleanup tự động.

## 6. Policy enforcement (policy.yaml)

### 6.1. Schema

```yaml
users:
  username:
    role: role_name

roles:
  role_name:
    allow:
      - command1
      - command2
```

### 6.2. Ví dụ

```yaml
users:
  admin:
    role: admin
  operator:
    role: operator
  auditor:
    role: auditor

roles:
  admin:
    allow: [init, backup, restore, verify, audit-verify]
  operator:
    allow: [backup, restore, verify]
  auditor:
    allow: [verify, audit-verify]
```

Nếu user không có quyền thực thi lệnh:

- Lệnh bị từ chối
- Audit log ghi trạng thái DENY

## 7. Audit log và audit-verify

### 7.1. Định dạng audit log

Mỗi dòng trong audit.log:

- ENTRY_HASH PREV_HASH UNIX_MS USER COMMAND ARGS_SHA256 STATUS

### 7.2. Cách tính hash

ENTRY_HASH = H(PREV_HASH || UNIX_MS || USER || COMMAND || ARGS_SHA256 || STATUS)

Audit log là append-only hash chain, mọi sửa đổi đều bị phát hiện.

### 7.3. Verify audit log

```bash
python3 -m src.main audit-verify
```

## 8. Xác định USER từ hệ điều hành

Chương trình xác định user theo thứ tự ưu tiên:

- Biến môi trường SUDO_USER (nếu chạy bằng sudo)
- User hiện tại của hệ điều hành (getpass.getuser())

Cách này đảm bảo audit log ghi đúng người thực sự thao tác.

## 9. Giới hạn hệ thống

- Không mã hóa dữ liệu
- Không chống admin chỉnh sửa policy hoặc source code
- Không hỗ trợ nhiều tiến trình ghi song song
- Không chống rollback cấp thiết bị
- Không bảo vệ khỏi xóa toàn bộ thư mục store