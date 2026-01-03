# Secure Backup & Recovery CLI

## 1. Mục tiêu
Xây dựng chương trình CLI sao lưu và phục hồi thư mục theo snapshot, đảm bảo:
- Toàn vẹn dữ liệu (Merkle Tree)
- Chống rollback
- An toàn khi crash (WAL)
- Kiểm soát thao tác bằng policy
- Audit log append-only có hash chain

## 2. Cài đặt
```bash
pip install -r requirements.txt
