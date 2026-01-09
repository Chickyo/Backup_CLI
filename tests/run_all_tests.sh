#!/bin/bash
chmod +x tests/*.sh

echo "========================================"
echo "RUNNING ALL TESTS FOR BACKUP CLI PROJECT"
echo "========================================"

./tests/test_tamper.sh
echo "----------------------------------------"
./tests/test_manifest_tamper.sh
echo "----------------------------------------"
./tests/test_rollback.sh
echo "----------------------------------------"
./tests/test_audit.sh
echo "----------------------------------------"
./tests/test_crash.sh
echo "----------------------------------------"
python3 tests/test_policy.py
echo "----------------------------------------"
./tests/generate_dataset.sh
echo "----------------------------------------"
./tests/test_restore.sh
echo "----------------------------------------"
echo "DONE."