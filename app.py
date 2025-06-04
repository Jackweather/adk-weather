from flask import Flask, send_from_directory, jsonify, make_response
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
PNG_DIR_RH = os.path.join("Hrrr", "static", "RH")  # Added for RH
PNG_DIR_HAIL = os.path.join("Hrrr", "static", "HAIL")  # Added for HAIL
PNG_DIR_CAPE = os.path.join("Hrrr", "static", "cape")  # Add this line near other PNG_DIR_*
PNG_DIR_CIN = os.path.join("Hrrr", "static", "cin")    # Add CIN directory
COLORBAR_DIR = os.path.join(BASE_DIR, "colorbars")  # Serve from project root colorbars folder

@app.route("/")
def home():
    return send_from_directory(BASE_DIR, "usa_leaflet.html")

@app.route("/reflectivity_images")
def get_pngs():
    # Find all REFC, MSLP, 2mtemp, Lightning, RH, HAIL, CAPE, and CIN PNGs by hour
    refc_files = [f for f in os.listdir(PNG_DIR_REFC) if re.match(r"REFC_(\d+)\.png$", f)]
    mslp_files = [f for f in os.listdir(PNG_DIR_MSLP) if re.match(r"MSLP_(\d+)\.png$", f)]
    temp2m_files = [f for f in os.listdir(PNG_DIR_TEMP2M) if re.match(r"2mtemp_(\d+)\.png$", f)]
    lightning_files = [f for f in os.listdir(PNG_DIR_LIGHTNING) if re.match(r"lght_(\d+)\.png$", f)]
    rh_files = [f for f in os.listdir(PNG_DIR_RH) if re.match(r"RH_(\d+)\.png$", f)]  # RH
    hail_files = [f for f in os.listdir(PNG_DIR_HAIL) if re.match(r"HAIL_(\d+)\.png$", f)]  # HAIL
    cape_files = [f for f in os.listdir(PNG_DIR_CAPE) if re.match(r"cape_(\d+)\.png$", f)]  # CAPE
    cin_files = [f for f in os.listdir(PNG_DIR_CIN) if re.match(r"cin_(\d+)\.png$", f)]    # CIN

    # Use regex to extract hour from each filename (more robust)
    def extract_hour(pattern, filename):
        m = re.match(pattern, filename)
        return int(m.group(1)) if m else None

    refc_dict = {extract_hour(r"REFC_(\d+)\.png$", f): f for f in refc_files}
    mslp_dict = {extract_hour(r"MSLP_(\d+)\.png$", f): f for f in mslp_files}
    temp2m_dict = {extract_hour(r"2mtemp_(\d+)\.png$", f): f for f in temp2m_files}
    lightning_dict = {extract_hour(r"lght_(\d+)\.png$", f): f for f in lightning_files}
    rh_dict = {extract_hour(r"RH_(\d+)\.png$", f): f for f in rh_files}  # RH
    hail_dict = {extract_hour(r"HAIL_(\d+)\.png$", f): f for f in hail_files}  # HAIL
    cape_dict = {extract_hour(r"cape_(\d+)\.png$", f): f for f in cape_files}  # CAPE
    cin_dict = {extract_hour(r"cin_(\d+)\.png$", f): f for f in cin_files}    # CIN

    # Remove None keys if any file didn't match pattern
    refc_dict = {k: v for k, v in refc_dict.items() if k is not None}
    mslp_dict = {k: v for k, v in mslp_dict.items() if k is not None}
    temp2m_dict = {k: v for k, v in temp2m_dict.items() if k is not None}
    lightning_dict = {k: v for k, v in lightning_dict.items() if k is not None}
    rh_dict = {k: v for k, v in rh_dict.items() if k is not None}  # RH
    hail_dict = {k: v for k, v in hail_dict.items() if k is not None}  # HAIL
    cape_dict = {k: v for k, v in cape_dict.items() if k is not None}  # CAPE
    cin_dict = {k: v for k, v in cin_dict.items() if k is not None}    # CIN

    # Union of all available hours from all overlays
    all_hours = set(refc_dict) | set(mslp_dict) | set(temp2m_dict) | set(lightning_dict) | set(rh_dict) | set(hail_dict) | set(cape_dict) | set(cin_dict)  # Add CIN
    all_hours = sorted(all_hours)

    result = []
    for hour in all_hours:
        result.append({
            "hour": hour,
            "refc": f"/refc_pngs/{refc_dict[hour]}" if hour in refc_dict else None,
            "mslp": f"/mslp_pngs/{mslp_dict[hour]}" if hour in mslp_dict else None,
            "temp2m": f"/temp2m_pngs/{temp2m_dict[hour]}" if hour in temp2m_dict else None,
            "lightning": f"/lightning_pngs/{lightning_dict[hour]}" if hour in lightning_dict else None,
            "rh": f"/rh_pngs/{rh_dict[hour]}" if hour in rh_dict else None,
            "hail": f"/hail_pngs/{hail_dict[hour]}" if hour in hail_dict else None,
            "cape": f"/cape_pngs/{cape_dict[hour]}" if hour in cape_dict else None,  # CAPE
            "cin": f"/cin_pngs/{cin_dict[hour]}" if hour in cin_dict else None      # CIN
        })
    response = make_response(jsonify(result))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

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

@app.route("/rh_pngs/<path:filename>")  # RH
def serve_rh_png(filename):
    return send_from_directory(PNG_DIR_RH, filename)

@app.route("/hail_pngs/<path:filename>")  # HAIL
def serve_hail_png(filename):
    return send_from_directory(PNG_DIR_HAIL, filename)

@app.route("/cape_pngs/<path:filename>")  # CAPE
def serve_cape_png(filename):
    return send_from_directory(PNG_DIR_CAPE, filename)

@app.route("/cin_pngs/<path:filename>")  # CIN
def serve_cin_png(filename):
    return send_from_directory(PNG_DIR_CIN, filename)

@app.route("/colorbar/<path:filename>")
def serve_colorbar(filename):
    return send_from_directory(COLORBAR_DIR, filename)

@app.route("/cartopy_base.png")
def serve_cartopy_base():
    return send_from_directory(BASE_DIR, "cartopy_base.png")

@app.route("/run-task")
def run_task():
    def run_all_scripts():
        try:
            subprocess.run(["python", os.path.join(BASE_DIR, "REFC.py")], check=True)
            print("REFC.py ran successfully!")
        except subprocess.CalledProcessError:
            error_trace = traceback.format_exc()
            print(f"Error running REFC.py:\n{error_trace}")

        try:
            subprocess.run(["python", os.path.join(BASE_DIR, "mslp_script.py")], check=True)
            print("mslp_script.py ran successfully!")
        except subprocess.CalledProcessError:
            error_trace = traceback.format_exc()
            print(f"Error running mslp_script.py:\n{error_trace}")

        try:
            subprocess.run(["python", os.path.join(BASE_DIR, "temp2m.py")], check=True)
            print("temp2m.py ran successfully!")
        except subprocess.CalledProcessError:
            error_trace = traceback.format_exc()
            print(f"Error running temp2m.py:\n{error_trace}")

        try:
            subprocess.run(["python", os.path.join(BASE_DIR, "RH.py")], check=True)  # RH
            print("RH.py ran successfully!")
        except subprocess.CalledProcessError:
            error_trace = traceback.format_exc()
            print(f"Error running RH.py:\n{error_trace}")

        try:
            subprocess.run(["python", os.path.join(BASE_DIR, "HAIL.py")], check=True)  # HAIL
            print("HAIL.py ran successfully!")
        except subprocess.CalledProcessError:
            error_trace = traceback.format_exc()
            print(f"Error running HAIL.py:\n{error_trace}")

        try:
            subprocess.run(["python", os.path.join(BASE_DIR, "cape.py")], check=True)  # CAPE
            print("cape.py ran successfully!")
        except subprocess.CalledProcessError:
            error_trace = traceback.format_exc()
            print(f"Error running cape.py:\n{error_trace}")

        try:
            subprocess.run(["python", os.path.join(BASE_DIR, "LIGHTNING.py")], check=True)
            print("LIGHTNING.py ran successfully!")
        except subprocess.CalledProcessError:
            error_trace = traceback.format_exc()
            print(f"Error running LIGHTNING.py:\n{error_trace}")

    threading.Thread(target=run_all_scripts).start()
    return "All scripts started sequentially in background!", 200

@app.route("/run-task1")
def run_task1():
    def run_scripts():
        try:
            subprocess.run(["python", os.path.join(BASE_DIR, "REFC.py")], check=True)
            print("REFC.py ran successfully!")
        except subprocess.CalledProcessError:
            error_trace = traceback.format_exc()
            print(f"Error running REFC.py:\n{error_trace}")

        try:
            subprocess.run(["python", os.path.join(BASE_DIR, "mslp_script.py")], check=True)
            print("mslp_script.py ran successfully!")
        except subprocess.CalledProcessError:
            error_trace = traceback.format_exc()
            print(f"Error running mslp_script.py:\n{error_trace}")

        try:
            subprocess.run(["python", os.path.join(BASE_DIR, "cin.py")], check=True)    # CIN moved here
            print("cin.py ran successfully!")
        except subprocess.CalledProcessError:
            error_trace = traceback.format_exc()
            print(f"Error running cin.py:\n{error_trace}")

    threading.Thread(target=run_scripts).start()
    return "REFC.py, mslp_script.py, and cin.py started in background!", 200

@app.route("/run-task2")
def run_task2():
    def run_scripts():
        try:
            subprocess.run(["python", os.path.join(BASE_DIR, "temp2m.py")], check=True)
            print("temp2m.py ran successfully!")
        except subprocess.CalledProcessError:
            error_trace = traceback.format_exc()
            print(f"Error running temp2m.py:\n{error_trace}")

        try:
            subprocess.run(["python", os.path.join(BASE_DIR, "RH.py")], check=True)
            print("RH.py ran successfully!")
        except subprocess.CalledProcessError:
            error_trace = traceback.format_exc()
            print(f"Error running RH.py:\n{error_trace}")

    threading.Thread(target=run_scripts).start()
    return "temp2m.py and RH.py started in background!", 200

@app.route("/run-task3")
def run_task3():
    def run_scripts():
        try:
            subprocess.run(["python", os.path.join(BASE_DIR, "HAIL.py")], check=True)
            print("HAIL.py ran successfully!")
        except subprocess.CalledProcessError:
            error_trace = traceback.format_exc()
            print(f"Error running HAIL.py:\n{error_trace}")

        try:
            subprocess.run(["python", os.path.join(BASE_DIR, "cape.py")], check=True)
            print("cape.py ran successfully!")
        except subprocess.CalledProcessError:
            error_trace = traceback.format_exc()
            print(f"Error running cape.py:\n{error_trace}")

        try:
            subprocess.run(["python", os.path.join(BASE_DIR, "LCDC.py")], check=True)
            print("LCDC.py ran successfully!")
        except subprocess.CalledProcessError:
            error_trace = traceback.format_exc()
            print(f"Error running LCDC.py:\n{error_trace}")

        try:
            subprocess.run(["python", os.path.join(BASE_DIR, "MCDC.py")], check=True)
            print("MCDC.py ran successfully!")
        except subprocess.CalledProcessError:
            error_trace = traceback.format_exc()
            print(f"Error running MCDC.py:\n{error_trace}")

        try:
            subprocess.run(["python", os.path.join(BASE_DIR, "HCDC.py")], check=True)
            print("HCDC.py ran successfully!")
        except subprocess.CalledProcessError:
            error_trace = traceback.format_exc()
            print(f"Error running HCDC.py:\n{error_trace}")

        try:
            subprocess.run(["python", os.path.join(BASE_DIR, "LIGHTNING.py")], check=True)
            print("LIGHTNING.py ran successfully!")
        except subprocess.CalledProcessError:
            error_trace = traceback.format_exc()
            print(f"Error running LIGHTNING.py:\n{error_trace}")

    threading.Thread(target=run_scripts).start()
    return "HAIL.py, cape.py, LCDC.py, MCDC.py, HCDC.py, and LIGHTNING.py started in background!", 200

@app.route("/<path:filename>")
def serve_static_file(filename):
    return send_from_directory(BASE_DIR, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
