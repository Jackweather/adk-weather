from flask import Flask, send_from_directory, jsonify, make_response, send_file, abort, request
import os
import re
import subprocess
import threading
import traceback
import getpass
import io

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PNG_DIR = os.path.join(BASE_DIR, "HRRRUN", "Hrrr", "static", "pngs")
PNG_DIR_REFC = os.path.join(BASE_DIR, "HRRRUN", "Hrrr", "static", "REFC")
PNG_DIR_MSLP = os.path.join(BASE_DIR, "HRRRUN", "Hrrr", "static", "MSLP")
PNG_DIR_TEMP2M = os.path.join(BASE_DIR, "HRRRUN", "Hrrr", "static", "2mtemp")
PNG_DIR_LIGHTNING = os.path.join(BASE_DIR, "HRRRUN", "Hrrr", "static", "lighting")
PNG_DIR_RH = os.path.join(BASE_DIR, "HRRRUN", "Hrrr", "static", "RH")
PNG_DIR_HAIL = os.path.join(BASE_DIR, "HRRRUN", "Hrrr", "static", "HAIL")
PNG_DIR_CAPE = os.path.join(BASE_DIR, "HRRRUN", "Hrrr", "static", "cape")
PNG_DIR_CIN = os.path.join(BASE_DIR, "HRRRUN", "Hrrr", "static", "cin")
PNG_DIR_LCDC = os.path.join(BASE_DIR, "HRRRUN", "Hrrr", "static", "LCDC")
PNG_DIR_MCDC = os.path.join(BASE_DIR, "HRRRUN", "Hrrr", "static", "MCDC")
PNG_DIR_HCDC = os.path.join(BASE_DIR, "HRRRUN", "Hrrr", "static", "HCDC")
PNG_DIR_PRECIP = os.path.join(BASE_DIR, "HRRRUN", "Hrrr", "static", "PRECIP")
PNG_DIR_WIND10M = os.path.join(BASE_DIR, "HRRRUN", "Hrrr", "static", "WIND10M")
PNG_DIR_WIND10M_STATION = os.path.join(BASE_DIR, "HRRRUN", "Hrrr", "static", "wind_bars_station")
COLORBAR_DIR = os.path.join(BASE_DIR, "colorbars")
PNG_DIR_SRH = os.path.join(BASE_DIR, "HRRRUN", "Hrrr", "static", "HLCY")
PNG_DIR_PWAT = os.path.join(BASE_DIR, "HRRRUN", "Hrrr", "static", "PWAT")
PNG_DIR_GUST = os.path.join(BASE_DIR, "HRRRUN", "Hrrr", "static", "GUST")
# Add VUCSH_VVCSH directory
PNG_DIR_SHEAR_VECTOR = os.path.join(BASE_DIR, "HRRRUN", "Hrrr", "static", "VUCSH_VVCSH")
# Add NBM tmp_surface PNG directory
PNG_DIR_NBM_TMP_SURFACE = os.path.join(BASE_DIR, "NBM", "NBM", "static", "tmp_surface")
# Add NBM total precipitation PNG directory
PNG_DIR_NBM_TOT_PRECIP = os.path.join(BASE_DIR, "NBM", "NBM", "static", "tot_precip")
# Add NBM MAXREF PNG directory
PNG_DIR_NBM_MAXREF = os.path.join(BASE_DIR, "NBM", "NBM", "static", "MAXREF")

@app.route("/")
def home():
    # Serve HRRR.html as the default home page
    return send_from_directory(BASE_DIR, "HRRR.html")

@app.route("/reflectivity_images")
def get_pngs():
    # Helper to safely list files in a directory
    def safe_listdir(path):
        try:
            return os.listdir(path)
        except FileNotFoundError:
            print(f"Directory not found: {path}")
            return []
        except Exception as e:
            print(f"Error listing directory {path}: {e}")
            return []

    # Find all REFC, MSLP, 2mtemp, Lightning, RH, HAIL, CAPE, CIN, LCDC, MCDC, HCDC, PRECIP, and WIND10M PNGs by hour
    refc_files = [f for f in safe_listdir(PNG_DIR_REFC) if re.match(r"REFC_(\d+)\.png$", f)]
    mslp_files = [f for f in safe_listdir(PNG_DIR_MSLP) if re.match(r"MSLP_(\d+)\.png$", f)]
    temp2m_files = [f for f in safe_listdir(PNG_DIR_TEMP2M) if re.match(r"2mtemp_(\d+)\.png$", f)]
    lightning_files = [f for f in safe_listdir(PNG_DIR_LIGHTNING) if re.match(r"lght_(\d+)\.png$", f)]
    rh_files = [f for f in safe_listdir(PNG_DIR_RH) if re.match(r"RH_(\d+)\.png$", f)]  # RH
    hail_files = [f for f in safe_listdir(PNG_DIR_HAIL) if re.match(r"HAIL_(\d+)\.png$", f)]  # HAIL
    cape_files = [f for f in safe_listdir(PNG_DIR_CAPE) if re.match(r"cape_(\d+)\.png$", f)]  # CAPE
    cin_files = [f for f in safe_listdir(PNG_DIR_CIN) if re.match(r"cin_(\d+)\.png$", f)]    # CIN
    lcdc_files = [f for f in safe_listdir(PNG_DIR_LCDC) if re.match(r"LCDC_(\d+)\.png$", f)]
    mcdc_files = [f for f in safe_listdir(PNG_DIR_MCDC) if re.match(r"MCDC_(\d+)\.png$", f)]
    hcdc_files = [f for f in safe_listdir(PNG_DIR_HCDC) if re.match(r"HCDC_(\d+)\.png$", f)]
    precip_files = [f for f in safe_listdir(PNG_DIR_PRECIP) if re.match(r"PRECIP_(\d+)\.png$", f)]
    wind10m_files = [f for f in safe_listdir(PNG_DIR_WIND10M) if re.match(r"WIND10M_(\d+)\.png$", f)]  # WIND10M
    wind10m_station_files = [f for f in safe_listdir(PNG_DIR_WIND10M_STATION) if re.match(r"wind_barbs_(\d+)\.png$", f)]  # Wind barbs at stations
    srh_files = [f for f in safe_listdir(PNG_DIR_SRH) if re.match(r"HLCY_(\d+)\.png$", f)]  # SRH
    pwat_files = [f for f in safe_listdir(PNG_DIR_PWAT) if re.match(r"PWAT_(\d+)\.png$", f)]  # PWAT
    gust_files = [f for f in safe_listdir(PNG_DIR_GUST) if re.match(r"GUST_(\d+)\.png$", f)]  # GUST
    # Add wind shear vector files
    shear_vector_files = [f for f in safe_listdir(PNG_DIR_SHEAR_VECTOR) if re.match(r"ShearVectors_(\d+)\.png$", f)]
    # Add NBM 2mtemp files
    nbm_temp2m_files = [f for f in safe_listdir(PNG_DIR_NBM_TMP_SURFACE) if re.match(r"2mtemp_(\d+)\.png$", f)]
    # Add NBM total precipitation files
    nbm_totprecip_files = [f for f in safe_listdir(PNG_DIR_NBM_TOT_PRECIP) if re.match(r"totprecip_(\d+)\.png$", f)]
    # Add NBM MAXREF files
    nbm_maxref_files = [f for f in safe_listdir(PNG_DIR_NBM_MAXREF) if re.match(r"MAXREF_(\d+)\.png$", f)]

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
    wind10m_station_dict = {extract_hour(r"wind_barbs_(\d+)\.png$", f): f for f in wind10m_station_files}  # Wind barbs at stations
    srh_dict = {extract_hour(r"HLCY_(\d+)\.png$", f): f for f in srh_files}  # SRH
    pwat_dict = {extract_hour(r"PWAT_(\d+)\.png$", f): f for f in pwat_files}  # PWAT
    gust_dict = {extract_hour(r"GUST_(\d+)\.png$", f): f for f in gust_files}  # GUST
    # Add wind shear vector dict
    shear_vector_dict = {extract_hour(r"ShearVectors_(\d+)\.png$", f): f for f in shear_vector_files}
    # Add NBM 2mtemp dict
    nbm_temp2m_dict = {extract_hour(r"2mtemp_(\d+)\.png$", f): f for f in nbm_temp2m_files}
    # Add NBM total precipitation dict
    nbm_totprecip_dict = {extract_hour(r"totprecip_(\d+)\.png$", f): f for f in nbm_totprecip_files}
    # Add NBM MAXREF dict
    nbm_maxref_dict = {extract_hour(r"MAXREF_(\d+)\.png$", f): f for f in nbm_maxref_files}

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
    wind10m_station_dict = {k: v for k, v in wind10m_station_dict.items() if k is not None}  # Wind barbs at stations
    srh_dict = {k: v for k, v in srh_dict.items() if k is not None}  # SRH
    pwat_dict = {k: v for k, v in pwat_dict.items() if k is not None}  # PWAT
    gust_dict = {k: v for k, v in gust_dict.items() if k is not None}  # GUST
    # Add wind shear vector dict cleanup
    shear_vector_dict = {k: v for k, v in shear_vector_dict.items() if k is not None}
    # Add NBM 2mtemp dict cleanup
    nbm_temp2m_dict = {k: v for k, v in nbm_temp2m_dict.items() if k is not None}
    # Add NBM total precipitation dict cleanup
    nbm_totprecip_dict = {k: v for k, v in nbm_totprecip_dict.items() if k is not None}
    # Add NBM MAXREF dict cleanup
    nbm_maxref_dict = {k: v for k, v in nbm_maxref_dict.items() if k is not None}

    # Determine if this is an NBM or HRRR request based on Referer or User-Agent or query param
    is_nbm = False
    referer = request.headers.get("Referer", "")
    if "NBM.html" in referer or "nbm.html" in referer or request.args.get("model") == "nbm":
        is_nbm = True
    elif "HRRR.html" in referer or "hrrr.html" in referer or request.args.get("model") == "hrrr":
        is_nbm = False

    # Union of all available hours from all overlays (add nbm_temp2m_dict, nbm_totprecip_dict, nbm_maxref_dict)
    all_hours = set(refc_dict) | set(mslp_dict) | set(temp2m_dict) | set(lightning_dict) | set(rh_dict) | set(hail_dict) | set(cape_dict) | set(cin_dict) | set(lcdc_dict) | set(mcdc_dict) | set(hcdc_dict) | set(precip_dict) | set(wind10m_dict) | set(wind10m_station_dict) | set(srh_dict) | set(pwat_dict) | set(gust_dict) | set(shear_vector_dict) | set(nbm_temp2m_dict) | set(nbm_totprecip_dict) | set(nbm_maxref_dict)
    all_hours = sorted(all_hours)

    # --- Only include hours that match the model's step ---
    if is_nbm:
        all_hours = [h for h in all_hours if h is not None and h % 6 == 0 and 6 <= h <= 264]
    else:
        # HRRR: Always return 0-48 (inclusive), even if files are missing
        all_hours = list(range(0, 49))

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
            "wind10m": f"/wind10m_pngs/{wind10m_dict[hour]}" if hour in wind10m_dict else None,
            "wind10m_station": f"/wind10m_station_pngs/{wind10m_station_dict[hour]}" if hour in wind10m_station_dict else None,
            "srh": f"/srh_pngs/{srh_dict[hour]}" if hour in srh_dict else None,
            "pwat": f"/pwat_pngs/{pwat_dict[hour]}" if hour in pwat_dict else None,
            "gust": f"/gust_pngs/{gust_dict[hour]}" if hour in gust_dict else None,
            "shear_vector": f"/shear_vector_pngs/{shear_vector_dict[hour]}" if hour in shear_vector_dict else None,
            "nbm_temp2m": f"/nbm_tmp_surface_pngs/{nbm_temp2m_dict[hour]}" if hour in nbm_temp2m_dict else None,
            "nbm_totprecip": f"/nbm_totprecip_pngs/{nbm_totprecip_dict[hour]}" if hour in nbm_totprecip_dict else None,
            "nbm_maxref": f"/nbm_maxref_pngs/{nbm_maxref_dict[hour]}" if hour in nbm_maxref_dict else None,
        })
    response = make_response(jsonify(result))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

def log_and_serve(directory, filename):
    full_path = os.path.join(directory, filename)
    print(f"Trying to serve: {full_path}")
    if not os.path.isfile(full_path):
        print(f"File NOT FOUND: {full_path}")
    else:
        print(f"File FOUND: {full_path}")
    return send_from_directory(directory, filename)

def api_serve_image(directory, filename):
    import mimetypes
    full_path = os.path.join(directory, filename)
    print(f"API serving: {full_path}")
    if not os.path.isfile(full_path):
        print(f"File NOT FOUND: {full_path}")
        abort(404)
    mime = mimetypes.guess_type(full_path)[0] or "image/png"
    return send_file(full_path, mimetype=mime)

@app.route("/refc_pngs/<path:filename>")
def serve_refc_png(filename):
    return api_serve_image(PNG_DIR_REFC, filename)

@app.route("/mslp_pngs/<path:filename>")
def serve_mslp_png(filename):
    return api_serve_image(PNG_DIR_MSLP, filename)

@app.route("/temp2m_pngs/<path:filename>")
def serve_temp2m_png(filename):
    return api_serve_image(PNG_DIR_TEMP2M, filename)

@app.route("/lightning_pngs/<path:filename>")
def serve_lightning_png(filename):
    return api_serve_image(PNG_DIR_LIGHTNING, filename)

@app.route("/rh_pngs/<path:filename>")  # RH
def serve_rh_png(filename):
    return api_serve_image(PNG_DIR_RH, filename)

@app.route("/hail_pngs/<path:filename>")  # HAIL
def serve_hail_png(filename):
    return api_serve_image(PNG_DIR_HAIL, filename)

@app.route("/cape_pngs/<path:filename>")  # CAPE
def serve_cape_png(filename):
    return api_serve_image(PNG_DIR_CAPE, filename)

@app.route("/cin_pngs/<path:filename>")  # CIN
def serve_cin_png(filename):
    return api_serve_image(PNG_DIR_CIN, filename)

@app.route("/lcdc_pngs/<path:filename>")
def serve_lcdc_png(filename):
    return api_serve_image(PNG_DIR_LCDC, filename)

@app.route("/mcdc_pngs/<path:filename>")
def serve_mcdc_png(filename):
    return api_serve_image(PNG_DIR_MCDC, filename)

@app.route("/hcdc_pngs/<path:filename>")
def serve_hcdc_png(filename):
    return api_serve_image(PNG_DIR_HCDC, filename)

@app.route("/precip_pngs/<path:filename>")
def serve_precip_png(filename):
    return api_serve_image(PNG_DIR_PRECIP, filename)

@app.route("/wind10m_pngs/<path:filename>")  # WIND10M
def serve_wind10m_png(filename):
    return api_serve_image(PNG_DIR_WIND10M, filename)

@app.route("/wind10m_station_pngs/<path:filename>")
def serve_wind10m_station_png(filename):
    return api_serve_image(PNG_DIR_WIND10M_STATION, filename)

@app.route("/colorbar/<path:filename>")
def serve_colorbar(filename):
    return send_from_directory(COLORBAR_DIR, filename)

@app.route("/cartopy_base.png")
def serve_cartopy_base():
    return send_from_directory(BASE_DIR, "cartopy_base.png")

@app.route("/run-task1")
def run_task1():
    def run_all_scripts():
        print("Flask is running as user:", getpass.getuser())  # Print user for debugging
        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/HRRRUN/REFC.py"],
                check=True, cwd="/opt/render/project/src/HRRRUN",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            print("REFC.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running REFC.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)

        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/HRRRUN/mslp_script.py"],
                check=True, cwd="/opt/render/project/src/HRRRUN",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            print("mslp_script.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running mslp_script.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)

        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/HRRRUN/CIN.py"],
                check=True, cwd="/opt/render/project/src/HRRRUN",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            print("CIN.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running CIN.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)

        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/HRRRUN/temp2m.py"],
                check=True, cwd="/opt/render/project/src/HRRRUN",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            print("temp2m.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running temp2m.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", result.stderr)

        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/HRRRUN/RH.py"],
                check=True, cwd="/opt/render/project/src/HRRRUN",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            print("RH.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running RH.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)

        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/HRRRUN/HAIL.py"],
                check=True, cwd="/opt/render/project/src/HRRRUN",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            print("HAIL.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running HAIL.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)

        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/HRRRUN/cape.py"],
                check=True, cwd="/opt/render/project/src/HRRRUN",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            print("cape.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running cape.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)

        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/HRRRUN/LCDC.py"],
                check=True, cwd="/opt/render/project/src/HRRRUN",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            print("LCDC.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running LCDC.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)

        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/HRRRUN/MCDC.py"],
                check=True, cwd="/opt/render/project/src/HRRRUN",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            print("MCDC.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running MCDC.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)

        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/HRRRUN/HCDC.py"],
                check=True, cwd="/opt/render/project/src/HRRRUN",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            print("HCDC.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running HCDC.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)

        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/HRRRUN/LIGHTNING.py"],
                check=True, cwd="/opt/render/project/src/HRRRUN",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            print("LIGHTNING.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running LIGHTNING.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)

        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/HRRRUN/total_precip.py"],
                check=True, cwd="/opt/render/project/src/HRRRUN",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            print("total_precip.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running total_precip.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)

        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/HRRRUN/WIND10M.py"],
                check=True, cwd="/opt/render/project/src/HRRRUN",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            print("WIND10M.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running WIND10M.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)

        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/HRRRUN/wind_bars_stations.py"],
                check=True, cwd="/opt/render/project/src/HRRRUN",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            print("wind_bars_station.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running wind_bars_stations.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)

        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/HRRRUN/StormRelativeHelicity.py"],
                check=True, cwd="/opt/render/project/src/HRRRUN",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            print("StormRelativeHelicity.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running StormRelativeHelicity.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)

        # --- PWAT ---
        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/HRRRUN/PWAT.py"],
                check=True, cwd="/opt/render/project/src/HRRRUN",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            print("PWAT.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running PWAT.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)

        # --- GUST ---
        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/HRRRUN/GUST.py"],
                check=True, cwd="/opt/render/project/src/HRRRUN",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            print("GUST.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running GUST.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)

        # --- VUCSH_VVCSH ---
        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/HRRRUN/VUCSH_VVCSH.py"],
                check=True, cwd="/opt/render/project/src/HRRRUN",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            print("VUCSH_VVCSH.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running VUCSH_VVCSH.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)

    threading.Thread(target=run_all_scripts).start()
    # For synchronous debug, comment above and uncomment below:
    # run_all_scripts()
    # return "Ran scripts synchronously for testing"
    return "All scripts started sequentially in background!", 200

@app.route("/run-task2")
def run_task2():
    def run_nbm_scripts():
        print("Flask is running as user:", getpass.getuser())  # Print user for debugging
        # --- tmp_surface.py ---
        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/NBM/tmp_surface.py"],
                check=True, cwd="/opt/render/project/src/NBM",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            print("tmp_surface.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running tmp_surface.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)
        # --- tot_precip.py ---
        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/NBM/tot_precip.py"],
                check=True, cwd="/opt/render/project/src/NBM",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            print("tot_precip.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running tot_precip.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)
        # --- maxrefc.py ---
        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/NBM/maxrefc.py"],
                check=True, cwd="/opt/render/project/src/NBM",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            print("maxrefc.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running maxrefc.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)
    threading.Thread(target=run_nbm_scripts).start()
    return "NBM tmp_surface.py, tot_precip.py, and maxrefc.py started in background!", 200

@app.route("/<path:filename>")
def serve_static_file(filename):
    return send_from_directory(BASE_DIR, filename)

@app.route("/soundings_stations")
def soundings_stations():
    # Only return stations if .download_complete exists
    bufkit_dir = os.path.join(BASE_DIR, "Sounding", "bufkit_files")
    marker_path = os.path.join(bufkit_dir, ".download_complete")
    if not os.path.exists(marker_path):
        return jsonify([])  # No stations until download is complete

    stations = []
    from Sounding.mainsounding1 import parse_bufkit
    # Only consider files that actually exist and are .buf files
    for fname in os.listdir(bufkit_dir):
        if not fname.endswith(".buf"):
            continue
        path = os.path.join(bufkit_dir, fname)
        if not os.path.isfile(path):
            continue  # Skip if not a file
        try:
            with open(path, "r", encoding="utf-8") as f:
                header = "".join([next(f) for _ in range(30)])
            # Extract SLAT/SLON
            import re
            m = re.search(r"SLAT\s*=\s*([-\d.]+).*SLON\s*=\s*([-\d.]+)", header)
            if not m:
                continue
            lat = float(m.group(1))
            lon = float(m.group(2))
            # Only include if at least one valid sounding exists
            with open(path, "r", encoding="utf-8") as f2:
                raw = f2.read()
            soundings = parse_bufkit(raw)
            if not soundings:
                continue
            stations.append({"name": fname, "lat": lat, "lon": lon})
        except Exception:
            continue
    return jsonify(stations)
@app.route("/run_mainsounding", methods=["POST"])
def run_mainsounding():
    import subprocess
    script_path = os.path.join(BASE_DIR, "Sounding", "mainsounding1.py")
    try:
        subprocess.Popen(["python", script_path])
        return jsonify({"status": "started"}), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route("/skewt_image")
def skewt_image():
    station = request.args.get("station")
    time_idx = int(request.args.get("time", 0))
    if not station:
        return "Missing station", 400
    from Sounding.mainsounding1 import parse_bufkit, plot_skewt_from_bufkit
    bufkit_dir = os.path.join(BASE_DIR, "Sounding", "bufkit_files")
    bufkit_path = os.path.join(bufkit_dir, station)
    if not os.path.isfile(bufkit_path):
        return "Station file not found", 404
    with open(bufkit_path, "r", encoding="utf-8") as f:
        raw = f.read()
    soundings = parse_bufkit(raw)
    if not soundings:
        return "No soundings found", 404
    if time_idx < 0 or time_idx >= len(soundings):
        return "Invalid time index", 400
    img_bytes = plot_skewt_from_bufkit(bufkit_path, time_idx)
    return send_file(io.BytesIO(img_bytes), mimetype="image/png")

@app.route("/soundings_times")
def soundings_times():
    station = request.args.get("station")
    if not station:
        return jsonify([])
    from Sounding.mainsounding1 import parse_bufkit
    bufkit_dir = os.path.join(BASE_DIR, "Sounding", "bufkit_files")
    bufkit_path = os.path.join(bufkit_dir, station)
    if not os.path.isfile(bufkit_path):
        return jsonify([])
    with open(bufkit_path, "r", encoding="utf-8") as f:
        raw = f.read()
    soundings = parse_bufkit(raw)
    return jsonify([s.get("time", f"Time {i}") for i, s in enumerate(soundings)])

@app.route("/soundings_ready")
def soundings_ready():
    bufkit_dir = os.path.join(BASE_DIR, "Sounding", "bufkit_files")
    marker_path = os.path.join(bufkit_dir, ".download_complete")
    return jsonify({"ready": os.path.exists(marker_path)})

@app.route("/hrrr.html")
def serve_hrrr_html():
    return send_from_directory(BASE_DIR, "HRRR.html")

@app.route("/nbm.html")
def serve_nbm_html():
    return send_from_directory(BASE_DIR, "NBM.html")

@app.route("/srh_pngs/<path:filename>")
def serve_srh_png(filename):
    return api_serve_image(PNG_DIR_SRH, filename)

@app.route("/pwat_pngs/<path:filename>")
def serve_pwat_png(filename):
    return api_serve_image(PNG_DIR_PWAT, filename)

@app.route("/gust_pngs/<path:filename>")
def serve_gust_png(filename):
    return api_serve_image(PNG_DIR_GUST, filename)

@app.route("/shear_vector_pngs/<path:filename>")
def serve_shear_vector_png(filename):
    return api_serve_image(PNG_DIR_SHEAR_VECTOR, filename)

@app.route("/nbm_tmp_surface_pngs/<path:filename>")
def serve_nbm_tmp_surface_png(filename):
    # Serve the HRRR temp colorbar for colorbar.png requests
    if filename == "colorbar.png":
        return send_from_directory(COLORBAR_DIR, "TEMP_colorbar.png")
    return api_serve_image(PNG_DIR_NBM_TMP_SURFACE, filename)

@app.route("/nbm_totprecip_pngs/<path:filename>")
def serve_nbm_totprecip_png(filename):
    # Serve the colorbar for colorbar.png requests
    if filename == "colorbar.png":
        return send_from_directory(COLORBAR_DIR, "PRECIP_colorbar.png")
    return api_serve_image(PNG_DIR_NBM_TOT_PRECIP, filename)

@app.route("/nbm_maxref_pngs/<path:filename>")
def serve_nbm_maxref_png(filename):
    # Serve the colorbar for colorbar.png requests
    if filename == "colorbar.png":
        return send_from_directory(COLORBAR_DIR, "REFC_colorbar.png")
    return api_serve_image(PNG_DIR_NBM_MAXREF, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
