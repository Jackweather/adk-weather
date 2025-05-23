from flask import Flask, send_from_directory, jsonify
import os
import re
import subprocess
import threading
import traceback

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PNG_DIR = os.path.join("Hrrr", "static", "pngs")
PNG_DIR_REFC = os.path.join("Hrrr", "static", "REFC")
PNG_DIR_MSLP = os.path.join("Hrrr", "static", "MSLP")
PNG_DIR_TEMP2M = os.path.join("Hrrr", "static", "2mtemp")
PNG_DIR_LIGHTNING = os.path.join("Hrrr", "static", "lighting")
COLORBAR_DIR = os.path.join(BASE_DIR, "colorbars")  # Serve from project root colorbars folder

@app.route("/")
def home():
    return send_from_directory(BASE_DIR, "usa_leaflet.html")

@app.route("/reflectivity_images")
def get_pngs():
    # Find all REFC, MSLP, 2mtemp, and Lightning PNGs by hour
    refc_files = [f for f in os.listdir(PNG_DIR_REFC) if re.match(r"REFC_(\d+)\.png$", f)]
    mslp_files = [f for f in os.listdir(PNG_DIR_MSLP) if re.match(r"MSLP_(\d+)\.png$", f)]
    temp2m_files = [f for f in os.listdir(PNG_DIR_TEMP2M) if re.match(r"2mtemp_(\d+)\.png$", f)]
    lightning_files = [f for f in os.listdir(PNG_DIR_LIGHTNING) if re.match(r"lght_(\d+)\.png$", f)]

    # Use regex to extract hour from each filename (more robust)
    def extract_hour(pattern, filename):
        m = re.match(pattern, filename)
        return int(m.group(1)) if m else None

    refc_dict = {extract_hour(r"REFC_(\d+)\.png$", f): f for f in refc_files}
    mslp_dict = {extract_hour(r"MSLP_(\d+)\.png$", f): f for f in mslp_files}
    temp2m_dict = {extract_hour(r"2mtemp_(\d+)\.png$", f): f for f in temp2m_files}
    lightning_dict = {extract_hour(r"lght_(\d+)\.png$", f): f for f in lightning_files}

    # Remove None keys if any file didn't match pattern
    refc_dict = {k: v for k, v in refc_dict.items() if k is not None}
    mslp_dict = {k: v for k, v in mslp_dict.items() if k is not None}
    temp2m_dict = {k: v for k, v in temp2m_dict.items() if k is not None}
    lightning_dict = {k: v for k, v in lightning_dict.items() if k is not None}

    # Union of all available hours from all overlays
    all_hours = set(refc_dict) | set(mslp_dict) | set(temp2m_dict) | set(lightning_dict)
    all_hours = sorted(all_hours)

    result = []
    for hour in all_hours:
        result.append({
            "hour": hour,
            "refc": f"/refc_pngs/{refc_dict[hour]}" if hour in refc_dict else None,
            "mslp": f"/mslp_pngs/{mslp_dict[hour]}" if hour in mslp_dict else None,
            "temp2m": f"/temp2m_pngs/{temp2m_dict[hour]}" if hour in temp2m_dict else None,
            "lightning": f"/lightning_pngs/{lightning_dict[hour]}" if hour in lightning_dict else None
        })
    return jsonify(result)

@app.route("/refc_pngs/<path:filename>")
def serve_refc_png(filename):
    return send_from_directory(PNG_DIR_REFC, filename)

@app.route("/mslp_pngs/<path:filename>")
def serve_mslp_png(filename):
    return send_from_directory(PNG_DIR_MSLP, filename)

@app.route("/temp2m_pngs/<path:filename>")
def serve_temp2m_png(filename):
    return send_from_directory(PNG_DIR_TEMP2M, filename)

@app.route("/lightning_pngs/<path:filename>")
def serve_lightning_png(filename):
    return send_from_directory(PNG_DIR_LIGHTNING, filename)

@app.route("/colorbar/<path:filename>")
def serve_colorbar(filename):
    return send_from_directory(COLORBAR_DIR, filename)

@app.route("/cartopy_base.png")
def serve_cartopy_base():
    return send_from_directory(BASE_DIR, "cartopy_base.png")

app.route("/run-task")
def run_test_script():
    def run_script():
        try:
            subprocess.run(["python", "REFC.py"], check=True)
            print("test.py ran successfully!")
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running test.py asynchronously:\n{error_trace}")

    threading.Thread(target=run_script).start()
    return "REFC.py started in background!", 200
@app.route("/<path:filename>")
def serve_static_file(filename):
    return send_from_directory(BASE_DIR, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
