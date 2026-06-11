# 9Router Qoder Fallback Patch

Patch untuk [9Router](https://www.npmjs.com/package/9router) AI gateway agar otomatis **fallback ke akun berikutnya** saat Qoder return 403 queue error (`isQueued`/`10605`), bukan return error JSON mentah ke client.

## Masalah

Saat Qoder overloaded, API return error seperti ini:
```
[qoder error 403: {"code":"403","message":"{"code":"10605","message":"{\"isQueued\":true,\"modelKey\":\"qmodel_latest\",\"queueCount\":2145,\"queueType\":\"slow\",\"serviceAvailable\"...
```

Default behavior 9Router:
- ❌ Error JSON mentah langsung di-pass ke client
- ❌ Akun di-lock dengan exponential backoff (terlalu lama)
- ❌ Buang waktu 3x retry refresh credentials (padahal bukan masalah auth)

## Solusi

Setelah patch:
- ✅ **Auto fallback** ke akun Qoder berikutnya (dari ratusan akun)
- ✅ **Cooldown cuma 5 detik** (bukan exponential backoff)
- ✅ **Error message bersih**: `"Qoder queue full (2145 waiting), retrying next account"`
- ✅ Tidak penalize akun — langsung bisa dipakai lagi setelah cooldown

## Cara Pakai

### Windows (Double-click)
1. Download folder ini
2. Double-click `9router-qoder-patch.bat`
3. Pilih menu:
   - **[1] Apply patch** — fix Qoder queue errors
   - **[2] Check status** — lihat apakah patch aktif
   - **[3] Revert patch** — restore original files
   - **[4] Test API** — kirim test request ke Qoder

### Command Line (Cross-platform)
```bash
# Cek status patch
python 9router-qoder-patch.py --check

# Apply patch
python 9router-qoder-patch.py --apply

# Revert ke original
python 9router-qoder-patch.py --revert

# Custom chunks directory (misal di VPS)
python 9router-qoder-patch.py --apply --chunks-dir /path/to/chunks
```

### Deploy ke Server Lain
```bash
python 9router-qoder-patch.py --apply --chunks-dir /path/to/9router/chunks
# Lalu restart 9router
```

## Setelah Apply

Restart 9router:
```bash
# Via PM2
pm2 restart 9router

# Atau manual
9router stop && 9router
```

## Technical Details

Patch memodifikasi 2 compiled chunk files di 9Router Next.js standalone build:

| Patch | Chunk | Function | Change |
|---|---|---|---|
| Queue detection | Module `2449` | `hk()` | Detect `isQueued`/`queueCount`/`10605` → 5s cooldown, no backoff |
| Error cleanup | Module `84514` | `vk()` | Replace raw Qoder JSON dengan clean message |

Script auto-detect chunk files berdasarkan **module ID** (bukan nama file), jadi tetap jalan walau chunk numbers berubah di versi 9Router baru.

## Compatibility

- ✅ 9Router v0.4.71 (tested)
- ✅ Windows, Linux, macOS
- ✅ Python 3.8+

## Notes

- ⚠️ Patch **hilang** setiap `npm i -g 9router@latest` — perlu apply ulang
- ⚠️ Backup otomatis dibuat (`.bak` files) sebelum patch
- ⚠️ Jika semua akun Qoder kena queue bersamaan, error message tetap bersih tapi tidak ada akun yang bisa di-fallback

## Files

```
├── 9router-qoder-patch.bat    ← Double-click (Windows)
├── 9router-qoder-patch.py     ← Script portable (cross-platform)
├── deploy-vps.py              ← Auto-deploy ke VPS via SSH
├── README.md                  ← File ini
└── LICENSE                    ← MIT
```

## License

MIT
