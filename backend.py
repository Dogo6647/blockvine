#!/usr/bin/env python3

from flask import Flask, render_template, request, jsonify, send_from_directory, abort, Response, redirect, make_response, url_for
import json
import os
import sys
import subprocess
import asyncio
import platform
import threading
import time
import hashlib
from pathlib import Path
import base64
import shutil

app = Flask(__name__, template_folder="gui", static_folder=None)

gui_dir = os.path.join(os.getcwd(), "gui")
global cur_proj_dir
cur_proj_dir = "none"
global action_queue
action_queue = []
watch_dir = os.path.expanduser("~/BlockVine")
os.makedirs(watch_dir, exist_ok=True)
state_file = "/tmp/known_sb3.json"


def rebuild_reload():
    print(f"Reloading!")
    try:
        subprocess.run([sys.executable, "sb3rebuild.py",
                       cur_proj_dir], check=True)
        print(f"Reload OK")
    except Exception as e:
        print(f"Failed to reload: {e}")
        return False
    action_queue.append("reload")
    return True


def break_sync():
    print(f"Syncing with editor!")
    try:
        if "BlockVine" in cur_proj_dir:
            cpd = Path(cur_proj_dir)
            shutil.rmtree(cpd / "src", ignore_errors=True)
            shutil.rmtree(cpd / "assets", ignore_errors=True)
            shutil.rmtree(cpd / "_bvcache", ignore_errors=True)
            subprocess.run([sys.executable, "sb3break.py",
                           f"{cur_proj_dir}.sb3"], check=True)
        else:
            raise Exception("Current project directory is not a BlockVine directory.")
        print(f"Sync OK")
    except Exception as e:
        print(f"Failed to sync: {e}")
        return False
    return True


IGNORED_DIRS = {"__pycache__", "_bvcache", ".git"}
IGNORED_SUFFIXES = {".pyc", ".tmp"}


def snapshot_dir(root):
    h = hashlib.sha256()

    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]

        for name in sorted(files):
            if name.endswith(tuple(IGNORED_SUFFIXES)):
                continue

            path = os.path.join(base, name)
            try:
                stat = os.stat(path)
                h.update(path.encode())
                h.update(str(stat.st_mtime).encode())
                h.update(str(stat.st_size).encode())
            except FileNotFoundError:
                pass

    return h.hexdigest()


def snapshot_file(path):
    try:
        stat = os.stat(path)
    except FileNotFoundError:
        return None

    h = hashlib.sha256()
    h.update(path.encode())
    h.update(str(stat.st_mtime).encode())
    h.update(str(stat.st_size).encode())
    return h.hexdigest()


def watch_project_dir():
    global cur_proj_dir, action_queue

    last_dir_hash = None
    last_sb3_hash = None

    while True:
        time.sleep(1)

        if not cur_proj_dir or cur_proj_dir == "none":
            continue
        if not os.path.isdir(cur_proj_dir):
            continue

        sb3_path = f"{cur_proj_dir}.sb3"

        try:
            dir_hash = snapshot_dir(cur_proj_dir)
            sb3_hash = snapshot_file(sb3_path)

            if last_dir_hash and dir_hash != last_dir_hash:
                rebuild_reload()
                sb3_hash = snapshot_file(sb3_path)

            if last_sb3_hash and sb3_hash != last_sb3_hash:
                break_sync()
                dir_hash = snapshot_dir(cur_proj_dir)

            last_dir_hash = dir_hash
            last_sb3_hash = sb3_hash

        except Exception as e:
            print(f"[Watcher] Error: {e}")


def get_known_files():
    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            try:
                return set(json.load(f))
            except json.JSONDecodeError:
                return set()
    return set()


def save_known_files(files):
    with open(state_file, "w") as f:
        json.dump(list(files), f)


def get_new_sb3_files():
    current_files = {f for f in os.listdir(watch_dir) if f.endswith(".sb3")}
    known = get_known_files()
    new = current_files - known
    if new:
        save_known_files(current_files)
    return list(new)


if os.path.exists(state_file):
    try:
        os.remove(state_file)
        print(f"Removed previous state file: {state_file}")
    except Exception as e:
        print(f"Could not remove {state_file}: {e}")
get_new_sb3_files()
exsb3 = get_known_files()
print(f"Existing SB3s found: {exsb3}")


def get_git(proj_dir):
    try:
        subprocess.run(["git", "-C", proj_dir, "rev-parse", "--is-inside-work-tree"],
                       check=True, capture_output=True)

        branches = subprocess.run(
            ["git", "-C", proj_dir, "branch", "-a",
                "--format", "%(refname:short)"],
            capture_output=True, text=True, check=True
        ).stdout.strip().split("\n")

        unstaged = subprocess.run(
            ["git", "-C", proj_dir, "status", "--porcelain"],
            capture_output=True, text=True, check=True
        ).stdout.strip().split("\n")

        branches = [b for b in branches if b]
        unstaged = [u for u in unstaged if u]

        return branches, unstaged

    except subprocess.CalledProcessError:
        return [], []


def get_git_history(proj_dir, limit=32):
    try:
        out = subprocess.run(
            [
                "git", "-C", proj_dir, "log",
                f"--max-count={limit}",
                "--pretty=format:%h|%an|%ad|%s",
                "--date=short"
            ],
            capture_output=True,
            text=True,
            check=True
        ).stdout.strip()

        commits = []
        for line in out.split("\n"):
            if not line:
                continue
            h, author, date, msg = line.split("|", 3)
            commits.append({
                "hash": h,
                "author": author,
                "date": date,
                "message": msg
            })

        return commits

    except subprocess.CalledProcessError:
        return []


def open_terminal(path=None, command=None):
    if path is None:
        path = os.getcwd()
    else:
        path = os.path.abspath(path)
    system = platform.system()
    try:
        if system == "Windows":
            subprocess.Popen(f'start cmd /K "cd /d {path}"', shell=True)
        elif system == "Darwin":
            subprocess.Popen([
                "osascript", "-e",
                f'tell application "Terminal" to do script "cd {path}"'
            ])
        elif system == "Linux":
            for term in ["gnome-terminal", "konsole",
                         "xfce4-terminal", "xterm"]:
                if subprocess.call(f"which {term}", shell=True,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
                    if term == "konsole":
                        subprocess.Popen(
                            [term, "--workdir", path] + (["-e", command] if command else []))
                        return "ok"
                    elif term == "gnome-terminal":
                        subprocess.Popen([term,
                                          f"--working-directory={path}"] + (["--",
                                                                             "bash",
                                                                             "-c",
                                                                             command] if command else []))
                        return "ok"
                    else:
                        subprocess.Popen([term, path, command])
                        return "ok"
            else:
                return ("No supported terminal emulator found.")
        else:
            return (f"Unsupported operating system: {system}")
    except Exception as e:
        print(f"Could not open terminal: {e}")


@app.route('/', methods=['GET'])
def ping():
    return "Pong!", 200


@app.route("/gui", defaults={"path": "index.html"})
@app.route("/gui/<path:path>")
def serve_file(path):
    global cur_proj_dir
    full_path = os.path.join(gui_dir, path)
    branches, unstaged = get_git(cur_proj_dir)
    history = get_git_history(cur_proj_dir)
    if not path.endswith(".html"):
        if os.path.isfile(full_path):
            return send_from_directory(gui_dir, path)
        else:
            return abort(404)
    if os.path.isfile(full_path):
        if not cur_proj_dir == "none":
            template_name = os.path.relpath(full_path, gui_dir)
        else:
            template_name = "onboarding.html"
        return render_template(
            template_name,
            projectDir=cur_proj_dir,
            projectName=cur_proj_dir.rsplit("/", 1)[-1],
            sys_username=subprocess.run(
                "whoami", capture_output=True, text=True).stdout,
            branches=branches or ["⚠️ No branches found."],
            unstaged=unstaged,
            history=history
        )
    else:
        return abort(404)


@app.route("/cmd/getInfo")
def getInfo():
    global cur_proj_dir, action_queue
    branches, unstaged = get_git(cur_proj_dir)
    history = get_git_history(cur_proj_dir)
    aq = action_queue.copy()
    action_queue.pop() if action_queue else None

    sb3_path = f"{cur_proj_dir}.sb3"
    projdata = None

    if os.path.exists(sb3_path):
        with open(sb3_path, "rb") as f:
            projdata = base64.b64encode(f.read()).decode("utf-8")

    return jsonify(
        path=cur_proj_dir,
        branches=branches,
        unstaged=unstaged,
        action_queue=aq,
        projdata=projdata,
        history=history
    ), 200


@app.route("/modal/folderpicker")
def md_folderpicker():
    home = os.path.expanduser("~")
    base_dir = os.path.join(home, "BlockVine")
    folders = [
        f for f in os.listdir(base_dir) if os.path.isdir(
            os.path.join(
                base_dir,
                f))]
    projects = [{"name": f, "path": os.path.join(
        base_dir, f)} for f in folders]
    return render_template("modals/folderpicker.html", projects=projects)


@app.route("/modal/convproject")
def md_convproject():
    return render_template("modals/convproject.html", sys_username=subprocess.run(
        "whoami", capture_output=True, text=True).stdout)


@app.route("/cmd/openProject", methods=['POST', 'GET'])
def openproject():
    global cur_proj_dir
    global action_queue
    cur_proj_dir = request.values.get('path')
    action_queue.append("reload")
    return redirect("/gui")


@app.route("/cmd/checkConv", methods=["POST", "GET"])
def checkconv():
    new_files = get_new_sb3_files()
    if not new_files:
        return make_response("", 204)
    else:
        # Redirect to streaming conversion view
        file_args = ",".join(new_files)
        conv_url = url_for("conview", files=file_args)
        return jsonify({"redirect": conv_url})


@app.route("/cmd/runConv/<files>")
def conview(files):
    file_list = files.split(",")
    print(f"[ Op ] Files to convert: {file_list}")

    def generate():
        yield """
        <html>
        <head><title>Converting...</title>
        <link rel=\"stylesheet\" href=\"/gui/assets/style.css\"
        </head><body>
        """
        for f in file_list:
            path = os.path.join(watch_dir, f)
            yield f"<h2>Converting {f}...</h2>"
            print(f"\nRunning sb3break.py on {f}...\n")
            try:
                process = subprocess.Popen(
                    [sys.executable, "sb3break.py", path, "--git"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                for line in iter(process.stdout.readline, ""):
                    if line.startswith("[ "):
                        yield f"<div class=\"pane\"><h4>{line}</h4></div>"
                    print(f"[ Op ] {line}")
                process.wait()
                yield f"<div class=\"pane docked\"><h3>Finished</h3>{f}<br><br>"
                yield f"<button onclick=\"window.location='/modal/folderpicker'\">Continue</button></div></body></html>"
                print(f"\n--- Finished {f} ---\n")
            except Exception as e:
                yield f"<div class=\"pane p-error\"><h3>Error converting {f}</h3>{e}<br><br></div></body></html>"
                print(f"\nError running sb3break.py on {f}: {e}\n")

    return Response(generate(), mimetype='text/html')


@app.route("/cmd/stage", methods=["POST"])
def stage():
    global cur_proj_dir
    file = request.get_json().get("file")

    try:
        subprocess.run(
            ["git", "-C", cur_proj_dir, "add", file],
            check=True,
            capture_output=True,
            text=True
        )
        return "", 204

    except subprocess.CalledProcessError as e:
        msg = e.stderr or e.stdout or "Unknown git error"
        return msg, 500


@app.route("/cmd/unstage", methods=["POST"])
def unstage():
    global cur_proj_dir
    file = request.get_json().get("file")

    try:
        subprocess.run(
            ["git", "-C", cur_proj_dir, "restore", "--staged", file],
            check=True
        )
        return "", 204
    except subprocess.CalledProcessError as e:
        return str(e), 500


@app.route("/cmd/commit", methods=["POST"])
def commit():
    global cur_proj_dir
    global action_queue
    msg = request.get_json().get("message")

    try:
        subprocess.run(
            ["git", "-C", cur_proj_dir, "commit", "-m", msg],
            check=True,
            capture_output=True,
            text=True
        )
        # action_queue.append("reload")
        return "", 204
    except subprocess.CalledProcessError as e:
        return e.stderr or str(e), 500


@app.route("/cmd/push", methods=["POST"])
def push():
    global cur_proj_dir
    try:
        open_terminal(
            path=cur_proj_dir,
            command=f"git -C {cur_proj_dir} push origin")
        return "", 204
    except Exception as e:
        return str(e), 500


@app.route("/cmd/pull", methods=["POST"])
def pull():
    global cur_proj_dir
    try:
        open_terminal(
            path=cur_proj_dir,
            command=f"git -C {cur_proj_dir} pull origin"),
        return "", 204
    except Exception as e:
        return str(e), 500


@app.route("/cmd/checkout", methods=["POST"])
def checkout():
    global cur_proj_dir
    global action_queue
    branch = request.get_json().get("branch")

    try:
        subprocess.run(
            ["git", "-C", cur_proj_dir, "checkout", branch],
            check=True,
            capture_output=True,
            text=True
        )
        action_queue.append("reload")
        return "", 204

    except subprocess.CalledProcessError as e:
        msg = e.stderr or e.stdout or "Unknown git error"
        return msg, 500


@app.route("/cmd/openShell", methods=['POST', 'GET'])
def openshell():
    global cur_proj_dir
    print(cur_proj_dir)
    result = open_terminal(path=cur_proj_dir)
    if not result == "ok":
        return result, 500
    else:
        return "Shell OK", 200


if __name__ == '__main__':
    threading.Thread(target=watch_project_dir, daemon=True).start()
    app.run(host='127.0.0.1', port=8617, debug=True)
