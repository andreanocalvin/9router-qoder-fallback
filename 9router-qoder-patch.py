#!/usr/bin/env python3
"""
9Router Qoder Queue Error Fallback Patch
=========================================
Patches 9router compiled chunks to:
1. Detect Qoder queue errors (isQueued/queueCount/10605) and use short 5s cooldown
2. Clean up raw Qoder JSON error messages into human-readable format
3. Enable proper fallback to next account instead of passing raw errors

Usage:
    python 9router-qoder-patch.py [--apply|--revert|--check|--dry-run]
    python 9router-qoder-patch.py --apply              # Apply patches
    python 9router-qoder-patch.py --revert             # Restore from .bak
    python 9router-qoder-patch.py --check              # Check if patches are applied
    python 9router-qoder-patch.py --dry-run            # Show what would be changed
    python 9router-qoder-patch.py --chunks-dir /path   # Custom chunks directory

Compatible with: 9router v0.4.71+ (Next.js standalone build)
Author: Hermes auto-patch
"""

import os
import sys
import re
import shutil
import argparse
import glob
import json

# === PATCH DEFINITIONS ===
# These are the search/replace patterns for the compiled chunks.
# They use regex to find the target code regardless of minification differences.

PATCHES = [
    {
        "name": "hk() Qoder queue detection",
        "description": "Add Qoder queue error detection in shouldFallback logic (hk function)",
        "file_glob": "*.js",
        # Pattern to identify the chunk containing module 2449 (hk function)
        "identify": lambda content: "2449:(a,b,c)" in content and "hk:()" in content,
        # The search pattern (regex)
        "search": r'function e\(a,b,c=0\)\{let f=b\?\("string"==typeof b\?b:JSON\.stringify\(b\)\)\.toLowerCase\(\):"";for\(let b of d\.t2\)',
        # The replacement
        "replace": 'function e(a,b,c=0){let f=b?("string"==typeof b?b:JSON.stringify(b)).toLowerCase():"";if(f&&(f.includes("isqueued")||f.includes("queuecount")||f.includes("10605"))){return{shouldFallback:!0,cooldownMs:5e3,newBackoffLevel:0}}for(let b of d.t2)',
        "backup_suffix": ".bak",
    },
    {
        "name": "vk() Qoder error cleanup",
        "description": "Clean up raw Qoder JSON error messages in account lock function (vk)",
        "file_glob": "*.js",
        # Pattern to identify the chunk containing module 84514 (vk function)
        "identify": lambda content: "84514:(a,b,c)" in content and "vk:()" in content,
        # The search pattern - original code that stores error message
        "search": r'let q="string"==typeof c\?c\.slice\(0,(\d+)\):"Provider error"(,r=)',
        # The replacement - add Qoder error cleanup + use `let r=` instead of `,r=`
        "replace": 'let q="string"==typeof c?c.slice(0,200):"Provider error";if(q.includes("isQueued")||q.includes("10605")){let _qc=q.match(/queueCount["\\\\s:]+(\\\\d+)/);q=`Qoder queue full (${_qc?_qc[1]+" waiting":"high traffic"}), retrying next account`}let r=',
        "backup_suffix": ".bak",
    },
    {
        "name": "proxy loop error cleanup",
        "description": "Clean Qoder error in proxy fallback loop so client sees clean message",
        "file_glob": "*.js",
        "identify": lambda content: "55221:(a,b,c)" in content and "v.add(b.connectionId)" in content,
        "search": r'v\.add\(b\.connectionId\),w=u\.error,x=u\.status;continue',
        "replace": 'v.add(b.connectionId),w=u.error&&(u.error.includes("isQueued")||u.error.includes("10605"))?"Qoder queue full ("+((u.error.match(/queueCount["\\\\s:]+(\\\\d+)/)||[])[1]||"?")+" waiting), retrying next account":u.error,x=u.status;continue',
        "backup_suffix": ".bak",
    },
    {
        "name": "Qoder fallback console log",
        "description": "Add visible console log when Qoder queue fallback happens",
        "file_glob": "*.js",
        "identify": lambda content: "55221:(a,b,c)" in content and "trying fallback" in content,
        "search": r'p\.warn\("AUTH",`Account \$\{b\.connectionName\} unavailable \(\$\{u\.status\}\), trying fallback`\)',
        "replace": r'p.warn("AUTH",`Account ${b.connectionName} unavailable (${u.status}), trying fallback`),u.error&&(u.error.includes("isQueued")||u.error.includes("10605"))&&console.log(`\x1b[33m\u{1F504} [QODER FALLBACK] ${b.connectionName} queued (${((u.error.match(/queueCount["\\s:]+(\\d+)/)||[])[1]||"?")} in queue) \u2192 trying next account\x1b[0m`)',
        "backup_suffix": ".bak",
    },
    {
        "name": "allRateLimited path cleanup",
        "description": "Clean Qoder error when all accounts are already locked from previous requests",
        "file_glob": "*.js",
        "identify": lambda content: "55221:(a,b,c)" in content and "allRateLimited" in content,
        "search": r'let a=w\|\|b\.lastError\|\|"Unavailable",c=x\|\|Number\(b\.lastErrorCode\)',
        "replace": 'let a=w||b.lastError||"Unavailable";if(typeof a==="string"&&(a.includes("isQueued")||a.includes("10605")))a="Qoder queue full, all accounts busy - retry shortly",c=x||Number(b.lastErrorCode)',
        "backup_suffix": ".bak",
    },
    {
        "name": "combo handler cleanup",
        "description": "Clean Qoder error in combo model handler when all models fail",
        "file_glob": "*.js",
        "identify": lambda content: "48146:(a,b,c)" in content and "All combo models unavailable" in content,
        "search": r'let p=m&&m\.toLowerCase\(\)\.includes\("no credentials"\)\?503:o\|\|503,q=m\|\|"All combo models unavailable"',
        "replace": 'let p=m&&m.toLowerCase().includes("no credentials")?503:o||503,q=m||"All combo models unavailable";if(typeof q==="string"&&(q.includes("isQueued")||q.includes("10605")))q="Qoder queue full, all models busy - retry shortly"',
        "backup_suffix": ".bak",
    },
]


def find_chunks_dir(custom_dir=None):
    """Find the 9router chunks directory."""
    if custom_dir:
        return custom_dir

    # Common locations
    candidates = []

    # Windows (npm global)
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        candidates.append(os.path.join(appdata, "npm", "node_modules", "9router",
                                        "app", ".next-cli-build", "server", "chunks"))

    # macOS/Linux (npm global)
    home = os.path.expanduser("~")
    candidates.append(os.path.join(home, ".npm-global", "lib", "node_modules", "9router",
                                    "app", ".next-cli-build", "server", "chunks"))
    candidates.append(os.path.join("/usr", "lib", "node_modules", "9router",
                                    "app", ".next-cli-build", "server", "chunks"))
    candidates.append(os.path.join("/usr", "local", "lib", "node_modules", "9router",
                                    "app", ".next-cli-build", "server", "chunks"))

    # Also try nvm paths
    for nvm_dir in glob.glob(os.path.join(home, ".nvm", "versions", "node", "*",
                                           "lib", "node_modules", "9router",
                                           "app", ".next-cli-build", "server", "chunks")):
        candidates.append(nvm_dir)

    for d in candidates:
        if os.path.isdir(d):
            return d

    return None


def check_patches(chunks_dir):
    """Check which patches are already applied."""
    results = []
    for patch in PATCHES:
        applied = False
        target_file = None

        for js_file in glob.glob(os.path.join(chunks_dir, patch["file_glob"])):
            with open(js_file, "r", encoding="utf-8") as f:
                content = f.read()

            if patch["identify"](content):
                target_file = js_file
                # Check if the replacement text is already present
                if 'f.includes("isqueued")' in content and patch["name"].startswith("hk"):
                    applied = True
                elif 'q.includes("isQueued")' in content and patch["name"].startswith("vk"):
                    applied = True
                elif 'u.error.includes("isQueued")' in content and patch["name"].startswith("proxy"):
                    applied = True
                elif 'QODER FALLBACK' in content and patch["name"].startswith("Qoder"):
                    applied = True
                elif 'all accounts busy' in content and patch["name"].startswith("allRateLimited"):
                    applied = True
                elif 'all models busy' in content and patch["name"].startswith("combo"):
                    applied = True
                break

        results.append({
            "name": patch["name"],
            "applied": applied,
            "file": target_file,
        })

    return results


def apply_patches(chunks_dir, dry_run=False):
    """Apply all patches to the chunks directory."""
    results = []

    for patch in PATCHES:
        target_file = None
        content = None

        # Find the target file
        for js_file in glob.glob(os.path.join(chunks_dir, patch["file_glob"])):
            with open(js_file, "r", encoding="utf-8") as f:
                file_content = f.read()

            if patch["identify"](file_content):
                target_file = js_file
                content = file_content
                break

        if not target_file:
            results.append({
                "name": patch["name"],
                "status": "SKIP",
                "reason": "Target chunk not found",
            })
            continue

        # Check if already patched
        already_applied = False
        check = check_patches(chunks_dir)
        for c in check:
            if c["name"] == patch["name"] and c["applied"]:
                results.append({
                    "name": patch["name"],
                    "status": "SKIP",
                    "reason": "Already applied",
                    "file": os.path.basename(target_file),
                })
                already_applied = True
                break
        if already_applied:
            continue

        # Apply the patch
        replace_str = patch["replace"]
        # Use lambda to avoid re.subn interpreting \x, \u etc in replacement
        if "\\x" in replace_str or "\\u" in replace_str:
            new_content, count = re.subn(patch["search"], lambda m: replace_str, content)
        else:
            new_content, count = re.subn(patch["search"], replace_str, content)

        if count == 0:
            results.append({
                "name": patch["name"],
                "status": "FAIL",
                "reason": "Search pattern not found (chunk format may have changed)",
                "file": os.path.basename(target_file),
            })
            continue

        if dry_run:
            results.append({
                "name": patch["name"],
                "status": "DRY-RUN",
                "reason": f"Would modify {count} occurrence(s)",
                "file": os.path.basename(target_file),
            })
            continue

        # Create backup
        bak_file = target_file + patch["backup_suffix"]
        if not os.path.exists(bak_file):
            shutil.copy2(target_file, bak_file)

        # Write patched content
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(new_content)

        results.append({
            "name": patch["name"],
            "status": "OK",
            "reason": f"Patched {count} occurrence(s)",
            "file": os.path.basename(target_file),
            "backup": os.path.basename(bak_file),
        })

    return results


def revert_patches(chunks_dir):
    """Revert all patches from backup files."""
    results = []

    for patch in PATCHES:
        for js_file in glob.glob(os.path.join(chunks_dir, patch["file_glob"])):
            bak_file = js_file + patch["backup_suffix"]
            if os.path.exists(bak_file):
                shutil.copy2(bak_file, js_file)
                results.append({
                    "name": patch["name"],
                    "status": "REVERTED",
                    "file": os.path.basename(js_file),
                })
                break
        else:
            results.append({
                "name": patch["name"],
                "status": "SKIP",
                "reason": "No backup file found",
            })

    return results


def restart_9router():
    """Kill 9router process and restart it."""
    import subprocess
    import platform
    import time

    system = platform.system()
    print("\n🔄 Restarting 9router...")

    # Kill existing process on port 20128
    try:
        if system == "Windows":
            result = subprocess.run(
                ["netstat", "-ano"], capture_output=True, text=True
            )
            for line in result.stdout.splitlines():
                if ":20128" in line and "LISTENING" in line:
                    pid = line.strip().split()[-1]
                    print(f"  Killing PID {pid}...")
                    subprocess.run(["taskkill", "/F", "/PID", pid],
                                   capture_output=True)
        else:
            result = subprocess.run(
                ["lsof", "-ti", ":20128"], capture_output=True, text=True
            )
            for pid in result.stdout.strip().split():
                print(f"  Killing PID {pid}...")
                subprocess.run(["kill", "-9", pid], capture_output=True)
    except Exception as e:
        print(f"  Kill failed: {e}")

    time.sleep(2)

    # Restart
    try:
        if system == "Windows":
            # Start in background tray mode
            subprocess.Popen(
                ["9router", "--no-browser", "--skip-update", "--tray"],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        else:
            # Try PM2 first, fallback to direct
            r = subprocess.run(["pm2", "restart", "9router"],
                               capture_output=True, text=True)
            if r.returncode != 0:
                subprocess.Popen(
                    ["9router", "--no-browser", "--skip-update"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )

        print("  Waiting for startup...")
        time.sleep(4)

        # Health check
        import urllib.request
        resp = urllib.request.urlopen("http://localhost:20128/api/health", timeout=5)
        data = resp.read().decode()
        if '"ok":true' in data or '"ok": true' in data:
            print("  ✅ 9router restarted successfully!")
        else:
            print(f"  ⚠️  Health check: {data[:100]}")
    except Exception as e:
        print(f"  ⚠️  9router may still be starting: {e}")
        print("  Wait a few seconds and check http://localhost:20128")



def main():
    parser = argparse.ArgumentParser(description="9Router Qoder Queue Error Fallback Patch")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--apply", action="store_true", help="Apply patches")
    group.add_argument("--revert", action="store_true", help="Revert patches from backup")
    group.add_argument("--check", action="store_true", help="Check patch status")
    group.add_argument("--dry-run", action="store_true", help="Show what would be changed")
    parser.add_argument("--chunks-dir", type=str, help="Custom chunks directory path")
    parser.add_argument("--no-restart", action="store_true", help="Skip auto-restart after apply")

    args = parser.parse_args()

    # Find chunks directory
    chunks_dir = find_chunks_dir(args.chunks_dir)
    if not chunks_dir or not os.path.isdir(chunks_dir):
        print("❌ Chunks directory not found!")
        print(f"   Searched: {chunks_dir or 'default locations'}")
        print(f"   Use --chunks-dir /path/to/chunks to specify")
        sys.exit(1)

    print(f"📁 Chunks dir: {chunks_dir}")
    print()

    if args.check:
        results = check_patches(chunks_dir)
        for r in results:
            status = "✅ Applied" if r["applied"] else "⬜ Not applied"
            file_info = f" ({os.path.basename(r['file'])})" if r["file"] else ""
            print(f"  {status} | {r['name']}{file_info}")

    elif args.apply:
        results = apply_patches(chunks_dir)
        for r in results:
            icon = {"OK": "✅", "FAIL": "❌", "SKIP": "⏭️"}.get(r["status"], "❓")
            file_info = f" → {r.get('file', '')}" if r.get("file") else ""
            backup_info = f" (backup: {r['backup']})" if r.get("backup") else ""
            print(f"  {icon} {r['name']}{file_info}")
            print(f"     {r['status']}: {r['reason']}{backup_info}")

        ok_count = sum(1 for r in results if r["status"] == "OK")
        if ok_count > 0 and not args.no_restart:
            restart_9router()

    elif args.dry_run:
        results = apply_patches(chunks_dir, dry_run=True)
        for r in results:
            print(f"  🔍 {r['name']} → {r.get('file', '?')}: {r['reason']}")

    elif args.revert:
        results = revert_patches(chunks_dir)
        for r in results:
            icon = {"REVERTED": "↩️", "SKIP": "⏭️"}.get(r["status"], "❓")
            print(f"  {icon} {r['name']} → {r.get('file', '?')}: {r['status']}")

        reverted = sum(1 for r in results if r["status"] == "REVERTED")
        if reverted > 0 and not args.no_restart:
            restart_9router()


if __name__ == "__main__":
    main()
