from flask import Flask, render_template, request, jsonify, send_from_directory, abort, Response, redirect
import os
import subprocess
import asyncio

app = Flask(__name__, template_folder="gui", static_folder=None)

gui_dir = os.path.join(os.getcwd(), "gui")
global cur_proj_dir
cur_proj_dir = "none"

@app.route('/', methods=['GET'])
def ping():
    return "Pong!", 200

@app.route("/gui", defaults={"path": "index.html"})
@app.route("/gui/<path:path>")
def serve_file(path):
    global cur_proj_dir
    full_path = os.path.join(gui_dir, path)
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
            branches=["main", "dev", "feat-x"], # placeholder (obviously)
            untracked=["placeholder"] # um yeah this one too
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


@app.route("/cmd/openProject", methods=['POST', 'GET'])
def openproject():
    global cur_proj_dir
    cur_proj_dir = request.values.get('path')
    return redirect("/gui")


if __name__ == '__main__':
    app.run(port=8617, debug=True)
