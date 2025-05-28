from flask import Flask, send_from_directory, jsonify
import os
import re
import subprocess
import threading
import traceback

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PNG_DIR = os.path.join("Hrrr", "static", "pngs")

@app.route("/")
def home():
    return send_from_directory(BASE_DIR, "usa_leaflet.html")

@app.route("/reflectivity_images")
def get_pngs():
    files = [f for f in os.listdir(PNG_DIR) if re.match(r"reflectivity_(\d+)\.png$", f)]
    files.sort(key=lambda x: int(re.search(r"(\d+)", x).group()))
    return jsonify([f"/pngs/{f}" for f in files])

@app.route("/pngs/<path:filename>")
def serve_png(filename):
    return send_from_directory(PNG_DIR, filename)

@app.route("/run-task")
def run_test_script():
    def run_script():
        try:
            subprocess.run(["python", "test.py"], check=True)
            print("test.py ran successfully!")
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running test.py asynchronously:\n{error_trace}")

    threading.Thread(target=run_script).start()
    return "test.py started in background!", 200

@app.route("/<path:filename>")
def serve_static_file(filename):
    return send_from_directory(BASE_DIR, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
