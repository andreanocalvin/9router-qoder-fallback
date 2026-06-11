9Router Qoder Queue Error Fallback Patch
==========================================

Fix: Qoder 403 queue error (isQueued/10605) langsung fallback ke akun berikutnya,
     bukan return error JSON mentah ke client.

CARA PAKAI:
-----------
  Windows:  Double-click "9router-qoder-patch.bat"
  Linux:    python3 9router-qoder-patch.py --apply

MENU:
  [1] Apply patch   - Fix Qoder queue errors
  [2] Check status  - See if patch is active  
  [3] Revert patch  - Restore original files
  [4] Test API      - Send test request to Qoder

SETelah APPLY:
  Restart 9router:  9router stop && 9router

CATATAN:
  - Patch hilang setiap "npm i -g 9router@latest"
  - Re-apply: double-click .bat lagi, pilih 1
  - Backup otomatis dibuat (.bak files)

FILE:
  9router-qoder-patch.bat  ← Double-click ini (Windows)
  9router-qoder-patch.py   ← Script Python (cross-platform)
  README.txt               ← File ini
