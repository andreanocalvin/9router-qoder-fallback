# 9Router Qoder Fallback Patch

Patch untuk [9Router](https://www.npmjs.com/package/9router) supaya otomatis **fallback ke akun berikutnya** saat Qoder return 403 queue error, bukan return error JSON mentah ke client.

## Problem

Saat Qoder overloaded, default 9Router:
- ❌ Error JSON mentah langsung ke client
- ❌ Akun di-lock terlalu lama (exponential backoff)
- ❌ Buang waktu retry refresh credentials

## Solution

- ✅ Auto fallback ke akun Qoder berikutnya
- ✅ Cooldown cuma 5 detik (bukan exponential backoff)
- ✅ Error message bersih & informatif
- ✅ Fallback log muncul di console log 9Router
- ✅ Auto-restart 9Router setelah patch

## Quick Start

### Windows
1. Download folder ini (atau `git clone`)
2. Double-click **`start.bat`**
3. Pilih **1** (Apply patch)
4. Done! 9Router auto-restart dengan patch aktif

### Command Line
```bash
# Apply + auto-restart
python 9router-qoder-patch.py --apply

# Check status
python 9router-qoder-patch.py --check

# Revert
python 9router-qoder-patch.py --revert

# Skip auto-restart
python 9router-qoder-patch.py --apply --no-restart

# Custom chunks directory
python 9router-qoder-patch.py --apply --chunks-dir /path/to/chunks
```

### Stress Test
```bash
python stress-test.py
```
Bombardir 50 request ke Qoder buat test apakah fallback bekerja.

## Patches (7 total)

| # | Patch | Effect |
|---|---|---|
| 1 | `hk()` queue detection | 5s cooldown, no exponential backoff |
| 2 | `vk()` DB cleanup | Clean error message in database |
| 3 | Proxy loop cleanup | Clean error when fallback active |
| 4 | Console log | `🔄 [QODER FALLBACK]` in terminal |
| 5 | allRateLimited cleanup | Clean error when all accounts locked |
| 6 | Combo handler cleanup | Clean error when combo models all fail |
| 7 | Dashboard log | `[QODER] FALLBACK` in 9Router console |

## Compatibility

- 9Router v0.4.71 (tested)
- Windows, Linux, macOS
- Python 3.8+

## Notes

- ⚠️ Patch hilang setiap `npm i -g 9router@latest` — run `start.bat` lagi
- Backup otomatis dibuat (`.bak` files) sebelum patch
- Kalau semua akun Qoder queued bareng, error tetap bersih tapi nggak ada akun yang bisa di-fallback

## License

MIT
