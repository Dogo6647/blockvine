#!/usr/bin/env python3

from flask import Flask, render_template, request, jsonify, send_from_directory, abort, Response, redirect, make_response, url_for
import json
import os
import subprocess
import asyncio
import platform

app = Flask(__name__, template_folder="gui", static_folder=None)

gui_dir = os.path.join(os.getcwd(), "gui")
global cur_proj_dir
cur_proj_dir = "none"
watch_dir = os.path.expanduser("~/BlockVine")
state_file = "/tmp/known_sb3.json"

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
            ["git", "-C", proj_dir, "branch", "-a", "--format", "%(refname:short)"],
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

def open_terminal(path=None):
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
            for term in ["gnome-terminal", "konsole", "xfce4-terminal", "xterm"]:
                if subprocess.call(f"which {term}", shell=True,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
                    subprocess.Popen([term, "--workdir", path])
                    break
            else:
                return("No supported terminal emulator found.")
        else:
            return(f"Unsupported operating system: {system}")
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
            projectDir = cur_proj_dir,
            projectName = cur_proj_dir.rsplit("/", 1)[-1],
            sys_username = subprocess.run("whoami", capture_output=True, text=True).stdout,
            branches=branches or ["⚠️ No branches found."],
            unstaged=unstaged
        )
    else:
        return abort(404)

@app.route("/modal/folderpicker")
def md_folderpicker():
    home = os.path.expanduser("~")
    base_dir = os.path.join(home, "BlockVine")
    folders = [f for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f))]
    projects = [{"name": f, "path": os.path.join(base_dir, f)} for f in folders]
    return render_template("modals/folderpicker.html", projects=projects)

@app.route("/modal/convproject")
def md_convproject():
    return render_template("modals/convproject.html", sys_username=subprocess.run("whoami", capture_output=True, text=True).stdout)


@app.route("/cmd/openProject", methods=['POST', 'GET'])
def openproject():
    global cur_proj_dir
    cur_proj_dir = request.values.get('path')
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
                    ["python3", "sb3break.py", path, "--git"],
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

@app.route("/cmd/openShell", methods=['POST', 'GET'])
def openshell():
    global cur_proj_dir
    print(cur_proj_dir)
    result = open_terminal(path=cur_proj_dir)
    if result:
        return result, 500
    else:
        return "Shell OK", 200

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8617, debug=True)
