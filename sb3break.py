#!/usr/bin/env python3

import os
import sys
import zipfile
import shutil
import json
import time
from pathlib import Path

try:
    from jsonbreak import disassemble_json
except ImportError:
    print("[ ⚠️ ] sb3break depends on jsonbreak.py. Make sure it’s in the same directory.")
    sys.exit(1)

def organize_sb3(sb3_path):
    sb3_path = Path(sb3_path).expanduser().resolve()
    if not sb3_path.exists() or sb3_path.suffix != ".sb3":
        print(f"[ ❌ ] {sb3_path} is an unsupported or nonexistent file.")
        return

    home = Path.home()
    if len(sys.argv) >= 3 and not sys.argv[2].startswith("--"):
        out_dir = Path(sys.argv[2])
    else:
        out_dir = home / "BlockVine" / sb3_path.stem
    assets_dir = out_dir / "assets"

    print(f"[ 🗜️ ] Extracting {sb3_path.name} to {out_dir}...")
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(sb3_path, 'r') as zip_ref:
        zip_ref.extractall(out_dir)

    subdirs = {
        "raster": assets_dir / "raster",
        "vector": assets_dir / "vector",
        "audio": assets_dir / "audio",
        "bgm": assets_dir / "bgm",
        "font": assets_dir / "font"
    }
    for d in subdirs.values():
        d.mkdir(parents=True, exist_ok=True)

    print("[ 📂 ] Sorting assets...")
    for file in out_dir.glob("*"):
        if not file.is_file():
            continue
        ext = file.suffix.lower()

        if ext in [".png", ".jpg", ".jpeg"]:
            shutil.move(str(file), subdirs["raster"] / file.name)

        elif ext == ".svg":
            shutil.move(str(file), subdirs["vector"] / file.name)

        elif ext in [".wav", ".mp3", ".ogg"]:
            try:
                import wave
                import contextlib
                if ext == ".wav":
                    with contextlib.closing(wave.open(str(file), 'r')) as f:
                        duration = f.getnframes() / float(f.getframerate())
                else:
                    # rough non-wav estimate using pydub
                    try:
                        from pydub import AudioSegment
                        duration = len(AudioSegment.from_file(file)) / 1000
                    except Exception:
                        duration = 0
                if duration <= 5:
                    shutil.move(str(file), subdirs["audio"] / file.name)
                else:
                    shutil.move(str(file), subdirs["bgm"] / file.name)
            except Exception as e:
                print(f"[ ⚠️ ] Unknown duration for file {file.name}: {e}")
                shutil.move(str(file), subdirs["audio"] / file.name)

        elif ext in [".ttf", ".otf", ".woff", ".woff2"]:
            shutil.move(str(file), subdirs["font"] / file.name)

    project_json = out_dir / "project.json"
    print("[ 🧩 ] Breaking up project JSON...")
    try:
        with open(project_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        disassemble_json(data, str(out_dir / "src"))
    except Exception as e:
        print(f"[ :( ] jsonbreak failed: {e}")

    if project_json.exists():
        project_json.unlink()
        print("[ 🧹 ] Cleanup: deleted original project.json")

    print(f"[ 😁 ] All done! Your project folder was generated at {out_dir}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python sb3break.py </path/to/sb3> [output_dir] [--git]")
        sys.exit(1)

    sb3_file = sys.argv[1]
    use_git = "--git" in sys.argv

    organize_sb3(sb3_file)

    if len(sys.argv) >= 3 and not sys.argv[2].startswith("--"):
        out_dir = Path(sys.argv[2]).expanduser().resolve()
    else:
        out_dir = Path.home() / "BlockVine" / Path(sb3_file).stem

    if use_git and not (out_dir / ".git").exists():
        import subprocess
        try:
            print("[ +🌱 ] Init Git...")
            subprocess.run(["git", "init", "-b", "main"], cwd=out_dir, check=True, stdout=subprocess.PIPE)
            gitignore_content = """# Python
__pycache__/
*.pyc
*.pyo

# macOS
.DS_Store

# Editor junk
*.swp
*.swo
.vscode/
.idea/

# BlockVine cache
_bvcache/
"""
            gitignore_path = out_dir / ".gitignore"
            gitignore_path.write_text(gitignore_content, encoding="utf-8")

            subprocess.run(["git", "add", "."], cwd=out_dir, check=True)
            subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=out_dir, check=True)

            print("[ +😁 ] Git repo initialized. Default branch is {main}.")
        except subprocess.CalledProcessError as e:
            print(f"[ +⚠️ ] Git init failed: {e}")
