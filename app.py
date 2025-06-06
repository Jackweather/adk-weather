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
PNG_DIR_LCDC = os.path.join("Hrrr", "static", "LCDC")
PNG_DIR_MCDC = os.path.join("Hrrr", "static", "MCDC")
PNG_DIR_HCDC = os.path.join("Hrrr", "static", "HCDC")
PNG_DIR_PRECIP = os.path.join("Hrrr", "static", "PRECIP")
PNG_DIR_WIND10M = os.path.join("Hrrr", "static", "WIND10M")  # Add this line for WIND10M
COLORBAR_DIR = os.path.join(BASE_DIR, "colorbars")  # Serve from project root colorbars folder



@app.route("/")
def home():
    return send_from_directory(BASE_DIR, "usa_leaflet.html")

@app.route("/reflectivity_images")
def get_pngs():
    # Find all REFC, MSLP, 2mtemp, Lightning, RH, HAIL, CAPE, CIN, LCDC, MCDC, HCDC, PRECIP, and WIND10M PNGs by hour
    refc_files = [f for f in os.listdir(PNG_DIR_REFC) if re.match(r"REFC_(\d+)\.png$", f)]
    mslp_files = [f for f in os.listdir(PNG_DIR_MSLP) if re.match(r"MSLP_(\d+)\.png$", f)]
    temp2m_files = [f for f in os.listdir(PNG_DIR_TEMP2M) if re.match(r"2mtemp_(\d+)\.png$", f)]
    lightning_files = [f for f in os.listdir(PNG_DIR_LIGHTNING) if re.match(r"lght_(\d+)\.png$", f)]
    rh_files = [f for f in os.listdir(PNG_DIR_RH) if re.match(r"RH_(\d+)\.png$", f)]  # RH
    hail_files = [f for f in os.listdir(PNG_DIR_HAIL) if re.match(r"HAIL_(\d+)\.png$", f)]  # HAIL
    cape_files = [f for f in os.listdir(PNG_DIR_CAPE) if re.match(r"cape_(\d+)\.png$", f)]  # CAPE
    cin_files = [f for f in os.listdir(PNG_DIR_CIN) if re.match(r"cin_(\d+)\.png$", f)]    # CIN
    lcdc_files = [f for f in os.listdir(PNG_DIR_LCDC) if re.match(r"LCDC_(\d+)\.png$", f)]
    mcdc_files = [f for f in os.listdir(PNG_DIR_MCDC) if re.match(r"MCDC_(\d+)\.png$", f)]
    hcdc_files = [f for f in os.listdir(PNG_DIR_HCDC) if re.match(r"HCDC_(\d+)\.png$", f)]
    precip_files = [f for f in os.listdir(PNG_DIR_PRECIP) if re.match(r"PRECIP_(\d+)\.png$", f)]
    wind10m_files = [f for f in os.listdir(PNG_DIR_WIND10M) if re.match(r"WIND10M_(\d+)\.png$", f)]  # WIND10M

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
    lcdc_dict = {extract_hour(r"LCDC_(\d+)\.png$", f): f for f in lcdc_files}
    mcdc_dict = {extract_hour(r"MCDC_(\d+)\.png$", f): f for f in mcdc_files}
    hcdc_dict = {extract_hour(r"HCDC_(\d+)\.png$", f): f for f in hcdc_files}
    precip_dict = {extract_hour(r"PRECIP_(\d+)\.png$", f): f for f in precip_files}
    wind10m_dict = {extract_hour(r"WIND10M_(\d+)\.png$", f): f for f in wind10m_files}  # WIND10M
    
    # Remove None keys if any file didn't match pattern
    refc_dict = {k: v for k, v in refc_dict.items() if k is not None}
    mslp_dict = {k: v for k, v in mslp_dict.items() if k is not None}
    temp2m_dict = {k: v for k, v in temp2m_dict.items() if k is not None}
    lightning_dict = {k: v for k, v in lightning_dict.items() if k is not None}
    rh_dict = {k: v for k, v in rh_dict.items() if k is not None}  # RH
    hail_dict = {k: v for k, v in hail_dict.items() if k is not None}  # HAIL
    cape_dict = {k: v for k, v in cape_dict.items() if k is not None}  # CAPE
    cin_dict = {k: v for k, v in cin_dict.items() if k is not None}    # CIN
    lcdc_dict = {k: v for k, v in lcdc_dict.items() if k is not None}
    mcdc_dict = {k: v for k, v in mcdc_dict.items() if k is not None}
    hcdc_dict = {k: v for k, v in hcdc_dict.items() if k is not None}
    precip_dict = {k: v for k, v in precip_dict.items() if k is not None}
    wind10m_dict = {k: v for k, v in wind10m_dict.items() if k is not None}  # WIND10M

    # Union of all available hours from all overlays
    all_hours = set(refc_dict) | set(mslp_dict) | set(temp2m_dict) | set(lightning_dict) | set(rh_dict) | set(hail_dict) | set(cape_dict) | set(cin_dict) | set(lcdc_dict) | set(mcdc_dict) | set(hcdc_dict) | set(precip_dict) | set(wind10m_dict)
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
            "cape": f"/cape_pngs/{cape_dict[hour]}" if hour in cape_dict else None,
            "cin": f"/cin_pngs/{cin_dict[hour]}" if hour in cin_dict else None,
            "lcdc": f"/lcdc_pngs/{lcdc_dict[hour]}" if hour in lcdc_dict else None,
            "mcdc": f"/mcdc_pngs/{mcdc_dict[hour]}" if hour in mcdc_dict else None,
            "hcdc": f"/hcdc_pngs/{hcdc_dict[hour]}" if hour in hcdc_dict else None,
            "precip": f"/precip_pngs/{precip_dict[hour]}" if hour in precip_dict else None,
            "wind10m": f"/wind10m_pngs/{wind10m_dict[hour]}" if hour in wind10m_dict else None  # WIND10M
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

@app.route("/lcdc_pngs/<path:filename>")
def serve_lcdc_png(filename):
    return send_from_directory(PNG_DIR_LCDC, filename)

@app.route("/mcdc_pngs/<path:filename>")
def serve_mcdc_png(filename):
    return send_from_directory(PNG_DIR_MCDC, filename)

@app.route("/hcdc_pngs/<path:filename>")
def serve_hcdc_png(filename):
    return send_from_directory(PNG_DIR_HCDC, filename)

@app.route("/precip_pngs/<path:filename>")
def serve_precip_png(filename):
    return send_from_directory(PNG_DIR_PRECIP, filename)

@app.route("/wind10m_pngs/<path:filename>")  # WIND10M
def serve_wind10m_png(filename):
    return send_from_directory(PNG_DIR_WIND10M, filename)

@app.route("/colorbar/<path:filename>")
def serve_colorbar(filename):
    return send_from_directory(COLORBAR_DIR, filename)

@app.route("/cartopy_base.png")
def serve_cartopy_base():
    return send_from_directory(BASE_DIR, "cartopy_base.png")

@app.route("/run-task1")
def run_task1():
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
            subprocess.run(["python", os.path.join(BASE_DIR, "CIN.py")], check=True)
            print("CIN.py ran successfully!")
        except subprocess.CalledProcessError:
            error_trace = traceback.format_exc()
            print(f"Error running CIN.py:\n{error_trace}")

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

        try:
            subprocess.run(["python", os.path.join(BASE_DIR, "total_precip.py")], check=True)
            print("total_precip.py ran successfully!")
        except subprocess.CalledProcessError:
            error_trace = traceback.format_exc()
            print(f"Error running total_precip.py:\n{error_trace}")

        try:
            subprocess.run(["python", os.path.join(BASE_DIR, "WIND10M.py")], check=True)
            print("WIND10M.py ran successfully!")
        except subprocess.CalledProcessError:
            error_trace = traceback.format_exc()
            print(f"Error running WIND10M.py:\n{error_trace}")
    threading.Thread(target=run_all_scripts).start()
    return "All scripts started sequentially in background!", 200

@app.route("/<path:filename>")
def serve_static_file(filename):
    return send_from_directory(BASE_DIR, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
