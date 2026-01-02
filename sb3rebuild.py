#!/usr/bin/env python3

import os
import sys
import shutil
import zipfile
from pathlib import Path
import json

sys.stdout.reconfigure(encoding="utf-8")

USE_EMOJI = os.name != "nt"  # windows can't print emojis to terminal or else it explodes

def icon(emoji, fallback):
    return emoji if USE_EMOJI else fallback

try:
    from jsonrebuild import rebuild_json
except ImportError:
    print(f"[ {icon('⚠️', 'WARN')} ] sb3rebuild depends on jsonrebuild.py. Make sure it’s in the same directory.")
    sys.exit(1)

def rebuild_sb3(project_dir):
    project_dir = Path(project_dir).expanduser().resolve()
    bvcache_dir = project_dir / "_bvcache"
    bvcache_dir.mkdir(parents=True, exist_ok=True)
    if not project_dir.exists():
        print(f"[ {icon('❌', 'ERROR')} ] Could not find {project_dir}")
        return

    assets_dir = project_dir / "assets"
    sb3_out = project_dir.with_suffix(".sb3")

    print(f"[ {icon('🧩', 'FOLDER')} ] Rebuilding JSON...")
    try:
        rebuiltjson = rebuild_json(str(project_dir / "src"))
        with open(str(bvcache_dir / "project.json"), "w", encoding="utf-8") as f:
            json.dump(rebuiltjson, f, separators=(',', ':'))
    except Exception as e:
        print(f"[ :( ] jsonrebuild.rebuild_json failed: {e}")
        return

    print(f"[ {icon('📤', 'FOLDER')} ] Moving assets back into the main directory...")
    for category in ["raster", "vector", "audio", "bgm", "font"]:
        src_dir = assets_dir / category
        if not src_dir.exists():
            continue
        for file in src_dir.glob("*"):
            if file.is_file():
                dest = bvcache_dir / file.name
                if dest.exists():
                    dest.unlink()
                shutil.copy(file, dest)

    print(f"[ {icon('🗜️', 'ZIP')} ] Repacking into an SB3 archive...")
    with zipfile.ZipFile(sb3_out, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in bvcache_dir.glob("*"):
            if file.is_file() and file.name != sb3_out.name:
                zipf.write(file, arcname=file.name)

    print(f"[ {icon('😁', 'OK')} ] All done! SB3 exported at ", sb3_out)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python sb3rebuild.py <path_to_unzipped_project_dir>")
        sys.exit(1)

    project_dir = sys.argv[1]
    rebuild_sb3(project_dir)
