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
# Add NBM GUST PNG directory
PNG_DIR_NBM_GUST = os.path.join(BASE_DIR, "NBM", "NBM", "static", "gust")
# Add NBM HAIL PNG directory
PNG_DIR_NBM_HAIL = os.path.join(BASE_DIR, "NBM", "NBM", "static", "hail")
# Add NBM Tornado PNG directory
PNG_DIR_NBM_TORNADO = os.path.join(BASE_DIR, "NBM", "NBM", "static", "tornado")
# Add NBM Thunderstorm Probability PNG directory
PNG_DIR_NBM_TSTM = os.path.join(BASE_DIR, "NBM", "NBM", "static", "tstm")
# Add NBM CAPE PNG directory
PNG_DIR_NBM_CAPE = os.path.join(BASE_DIR, "NBM", "NBM", "static", "cape")
# Add NBM Wind PNG directory
PNG_DIR_NBM_WIND = os.path.join(BASE_DIR, "NBM", "NBM", "static", "wind")


# Add these near the other RADAR_DIR definitions
RADAR_AVG_DIR = os.path.join(BASE_DIR, "Radar", "refcavg")   # Averaged radar images
RADAR_RAW_DIR = os.path.join(BASE_DIR, "Radar", "refcraw")   # Raw radar images

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
    # Add NBM GUST files
    nbm_gust_files = [f for f in safe_listdir(PNG_DIR_NBM_GUST) if re.match(r"gust_(\d+)\.png$", f)]
    # Add NBM HAIL files
    nbm_hail_files = [f for f in safe_listdir(PNG_DIR_NBM_HAIL) if re.match(r"hail_(\d+)\.png$", f)]
    # Add NBM Tornado files
    nbm_tornado_files = [f for f in safe_listdir(PNG_DIR_NBM_TORNADO) if re.match(r"tornado_(\d+)\.png$", f)]
    # Add NBM Thunderstorm Probability files
    nbm_tstm_files = [f for f in safe_listdir(PNG_DIR_NBM_TSTM) if re.match(r"tstm_(\d+)\.png$", f)]
    # Add NBM CAPE files
    nbm_cape_files = [f for f in safe_listdir(PNG_DIR_NBM_CAPE) if re.match(r"cape_(\d+)\.png$", f)]  # CAPE
    # Add NBM Wind files
    nbm_wind_files = [f for f in safe_listdir(PNG_DIR_NBM_WIND) if re.match(r"wind_(\d+)\.png$", f)]

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
    # Add NBM GUST dict
    nbm_gust_dict = {extract_hour(r"gust_(\d+)\.png$", f): f for f in nbm_gust_files}
    # Add NBM HAIL dict
    nbm_hail_dict = {extract_hour(r"hail_(\d+)\.png$", f): f for f in nbm_hail_files}
    # Add NBM Tornado dict
    nbm_tornado_dict = {extract_hour(r"tornado_(\d+)\.png$", f): f for f in nbm_tornado_files}
    # Add NBM Thunderstorm Probability dict
    nbm_tstm_dict = {extract_hour(r"tstm_(\d+)\.png$", f): f for f in nbm_tstm_files}
    # Add NBM CAPE dict
    nbm_cape_dict = {extract_hour(r"cape_(\d+)\.png$", f): f for f in nbm_cape_files}
    # Add NBM Wind dict
    nbm_wind_dict = {extract_hour(r"wind_(\d+)\.png$", f): f for f in nbm_wind_files}

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
    # Add NBM GUST dict cleanup
    nbm_gust_dict = {k: v for k, v in nbm_gust_dict.items() if k is not None}
    # Add NBM HAIL dict cleanup
    nbm_hail_dict = {k: v for k, v in nbm_hail_dict.items() if k is not None}
    # Add NBM Tornado dict cleanup
    nbm_tornado_dict = {k: v for k, v in nbm_tornado_dict.items() if k is not None}
    # Add NBM Thunderstorm Probability dict cleanup
    nbm_tstm_dict = {k: v for k, v in nbm_tstm_dict.items() if k is not None}
    # Add NBM CAPE dict cleanup
    nbm_cape_dict = {k: v for k, v in nbm_cape_dict.items() if k is not None}
    # Add NBM Wind dict cleanup
    nbm_wind_dict = {k: v for k, v in nbm_wind_dict.items() if k is not None}

    # Determine if this is an NBM or HRRR request based on Referer or User-Agent or query param
    is_nbm = False
    referer = request.headers.get("Referer", "")
    if "NBM.html" in referer or "nbm.html" in referer or request.args.get("model") == "nbm":
        is_nbm = True
    elif "HRRR.html" in referer or "hrrr.html" in referer or request.args.get("model") == "hrrr":
        is_nbm = False

    # --- Add support for archive mode ---
    archive = request.args.get("archive")
    archive_dir = None
    if archive:
        archive_dir = os.path.join(BASE_DIR, "HRRRSAVED", archive, "static")
        # Define archive overlay directories
        ARCHIVE_OVERLAY_DIRS = {
            "refc": os.path.join(archive_dir, "REFC"),
            "mslp": os.path.join(archive_dir, "MSLP"),
            "temp2m": os.path.join(archive_dir, "2mtemp"),
            "lightning": os.path.join(archive_dir, "lighting"),
            "rh": os.path.join(archive_dir, "RH"),
            "hail": os.path.join(archive_dir, "HAIL"),
            "cape": os.path.join(archive_dir, "cape"),
            "cin": os.path.join(archive_dir, "cin"),
            "lcdc": os.path.join(archive_dir, "LCDC"),
            "mcdc": os.path.join(archive_dir, "MCDC"),
            "hcdc": os.path.join(archive_dir, "HCDC"),
            "precip": os.path.join(archive_dir, "PRECIP"),
            "wind10m": os.path.join(archive_dir, "WIND10M"),
            "wind10m_station": os.path.join(archive_dir, "wind_bars_station"),
            "srh": os.path.join(archive_dir, "HLCY"),
            "pwat": os.path.join(archive_dir, "PWAT"),
            "gust": os.path.join(archive_dir, "GUST"),
            "shear_vector": os.path.join(archive_dir, "VUCSH_VVCSH"),
        }
        # Helper to safely list files in a directory
        def safe_listdir(path):
            try:
                return os.listdir(path)
            except Exception:
                return []
        # Build dicts for each overlay in archive
        archive_dicts = {}
        overlay_patterns = {
            "refc": r"REFC_(\d+)\.png$",
            "mslp": r"MSLP_(\d+)\.png$",
            "temp2m": r"2mtemp_(\d+)\.png$",
            "lightning": r"lght_(\d+)\.png$",
            "rh": r"RH_(\d+)\.png$",
            "hail": r"HAIL_(\d+)\.png$",
            "cape": r"cape_(\d+)\.png$",
            "cin": r"cin_(\d+)\.png$",
            "lcdc": r"LCDC_(\d+)\.png$",
            "mcdc": r"MCDC_(\d+)\.png$",
            "hcdc": r"HCDC_(\d+)\.png$",
            "precip": r"PRECIP_(\d+)\.png$",
            "wind10m": r"WIND10M_(\d+)\.png$",
            "wind10m_station": r"wind_barbs_(\d+)\.png$",
            "srh": r"HLCY_(\d+)\.png$",
            "pwat": r"PWAT_(\d+)\.png$",
            "gust": r"GUST_(\d+)\.png$",
            "shear_vector": r"ShearVectors_(\d+)\.png$",
        }
        for overlay, dirpath in ARCHIVE_OVERLAY_DIRS.items():
            files = [f for f in safe_listdir(dirpath) if re.match(overlay_patterns[overlay], f)]
            archive_dicts[overlay] = {int(re.match(overlay_patterns[overlay], f).group(1)): f for f in files if re.match(overlay_patterns[overlay], f)}
        # Union of all available hours in archive
        all_hours = set()
        for d in archive_dicts.values():
            all_hours |= set(d.keys())
        all_hours = sorted(all_hours)
        # Always return 0-48 for HRRR archive
        all_hours = list(range(0, 49))
        result = []
        for hour in all_hours:
            entry = {"hour": hour}
            for overlay in ARCHIVE_OVERLAY_DIRS:
                d = archive_dicts[overlay]
                entry[overlay] = f"/archive_pngs/{archive}/{overlay}/{d[hour]}" if hour in d else None
            # Fill in overlays not in archive as None
            for overlay in ["nbm_temp2m", "nbm_totprecip", "nbm_gust", "nbm_maxref", "nbm_hail", "nbm_tornado", "nbm_tstm", "nbm_cape", "nbm_wind"]:
                entry[overlay] = None
            result.append(entry)
        response = make_response(jsonify(result))
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    # Union of all available hours from all overlays (add nbm_temp2m_dict, nbm_totprecip_dict, nbm_maxref_dict, nbm_hail_dict, nbm_tornado_dict)
    all_hours = set(refc_dict) | set(mslp_dict) | set(temp2m_dict) | set(lightning_dict) | set(rh_dict) | set(hail_dict) | set(cape_dict) | set(cin_dict) | set(lcdc_dict) | set(mcdc_dict) | set(hcdc_dict) | set(precip_dict) | set(wind10m_dict) | set(wind10m_station_dict) | set(srh_dict) | set(pwat_dict) | set(gust_dict) | set(shear_vector_dict) | set(nbm_temp2m_dict) | set(nbm_totprecip_dict) | set(nbm_gust_dict) | set(nbm_maxref_dict) | set(nbm_hail_dict) | set(nbm_tornado_dict) | set(nbm_tstm_dict) | set(nbm_cape_dict) | set(nbm_wind_dict)
    all_hours = sorted(all_hours)

    # --- Only include hours that match the model's step ---
    if is_nbm:
        # NBM: Always return 6-264 (inclusive, every 6 hours), even if files are missing
        all_hours = list(range(6, 265, 6))
    elif "GFS.html" in referer or "gfs.html" in referer or request.args.get("model") == "gfs":
        # GFS: Always return 6-384 (inclusive, every 6 hours), even if files are missing
        all_hours = list(range(6, 385, 6))
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
            "nbm_gust": f"/nbm_gust_pngs/{nbm_gust_dict[hour]}" if hour in nbm_gust_dict else None,
            "nbm_maxref": f"/nbm_maxref_pngs/{nbm_maxref_dict[hour]}" if hour in nbm_maxref_dict else None,
            "nbm_hail": f"/nbm_hail_pngs/{nbm_hail_dict[hour]}" if hour in nbm_hail_dict else None,
            "nbm_tornado": f"/nbm_tornado_pngs/{nbm_tornado_dict[hour]}" if hour in nbm_tornado_dict else None,
            "nbm_tstm": f"/nbm_tstm_pngs/{nbm_tstm_dict[hour]}" if hour in nbm_tstm_dict else None,
            "nbm_cape": f"/nbm_cape_pngs/{nbm_cape_dict[hour]}" if hour in nbm_cape_dict else None,
            "nbm_wind": f"/nbm_wind_pngs/{nbm_wind_dict[hour]}" if hour in nbm_wind_dict else None,
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
        # --- Run HRRRSAVED/HRRRsaved.py first ---
        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/HRRRSAVED/HRRRsaved.py"],
                check=True, cwd="/opt/render/project/src/HRRRSAVED",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            print("HRRRsaved.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running HRRRsaved.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)
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
        # --- NBM_GUST.py ---
        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/NBM/NBM_GUST.py"],
                check=True, cwd="/opt/render/project/src/NBM",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            print("NBM_GUST.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running NBM_GUST.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)
        # --- NBM_HAIL.py ---
        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/NBM/NBM_HAIL.py"],
                check=True, cwd="/opt/render/project/src/NBM",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            print("NBM_HAIL.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running NBM_HAIL.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)
        # --- NBM_TORNADO.py ---
        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/NBM/NBM_TORNADO.py"],
                check=True, cwd="/opt/render/project/src/NBM",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            print("NBM_TORNADO.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running NBM_TORNADO.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)
        # --- NBM_TSTM.py ---
        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/NBM/NBM_TSTM.py"],
                check=True, cwd="/opt/render/project/src/NBM",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            print("NBM_TSTM.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running NBM_TSTM.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)
    threading.Thread(target=run_nbm_scripts).start()
    return "NBM tmp_surface.py, tot_precip.py, maxrefc.py, NBM_GUST.py, NBM_HAIL.py, NBM_TORNADO.py, and NBM_TSTM.py started in background!", 200

@app.route("/run-task3")
def run_task3():
    def run_radar_scripts():
        print("Flask is running as user:", getpass.getuser())  # Print user for debugging
        # --- RADAR/code/Newyork.py ---
        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/Radar/code/Newyork.py"],
                check=True,
                cwd="/opt/render/project/src/Radar/code",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print("Newyork.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running Newyork.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)
        # --- RADAR/code/Newyork_raw.py ---
        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/Radar/code/Newyork_raw.py"],
                check=True,
                cwd="/opt/render/project/src/Radar/code",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print("Newyork_raw.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running Newyork_raw.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)
    threading.Thread(target=run_radar_scripts).start()
    return "Radar/code/Newyork.py and Radar/code/Newyork_raw.py started in background!", 200

@app.route("/run-task4")
def run_task4():
    def run_nwsdiscmodel_script():
        print("Flask is running as user:", getpass.getuser())  # Print user for debugging
        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/weatherdata/nwsdiscmodel.py"],
                check=True,
                cwd="/opt/render/project/src/weatherdata",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print("nwsdiscmodel.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running nwsdiscmodel.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)
    threading.Thread(target=run_nwsdiscmodel_script).start()
    return "weatherdata/nwsdiscmodel.py started in background!", 200

@app.route("/run-task5")
def run_task5():
    def run_gfs_scripts():
        print("Flask is running as user:", getpass.getuser())  # Print user for debugging
        # --- GFS_ABSV.py ---
        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/GFS/GFS_ABSV.py"],
                check=True,
                cwd="/opt/render/project/src/GFS",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print("GFS_ABSV.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running GFS_ABSV.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)
        # --- gfs_precip_convective_accum.py ---
        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/GFS/gfs_precip_convective_accum.py"],
                check=True,
                cwd="/opt/render/project/src/GFS",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print("gfs_precip_convective_accum.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running gfs_precip_convective_accum.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)
        # --- gfs_precip_total_accum.py ---
        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/GFS/gfs_precip_total_accum.py"],
                check=True,
                cwd="/opt/render/project/src/GFS",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print("gfs_precip_total_accum.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running gfs_precip_total_accum.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)
        # --- gfs_precip24.py ---
        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/GFS/gfs_precip24.py"],
                check=True,
                cwd="/opt/render/project/src/GFS",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print("gfs_precip24.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running gfs_precip24.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)
        # --- gfs_total_precip.py ---
        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/GFS/gfs_total_precip.py"],
                check=True,
                cwd="/opt/render/project/src/GFS",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print("gfs_total_precip.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running gfs_total_precip.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)
        # --- HAINESCY.py ---
        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/GFS/HAINESCY.py"],
                check=True,
                cwd="/opt/render/project/src/GFS",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print("HAINESCY.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running HAINESCY.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)
        # --- hgt_500.py ---
        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/GFS/hgt_500.py"],
                check=True,
                cwd="/opt/render/project/src/GFS",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print("hgt_500.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running hgt_500.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)
        # --- mslp_surface.py ---
        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/GFS/mslp_surface.py"],
                check=True,
                cwd="/opt/render/project/src/GFS",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print("mslp_surface.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running mslp_surface.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)
        # --- REFCGFS.py ---
        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/GFS/REFCGFS.py"],
                check=True,
                cwd="/opt/render/project/src/GFS",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print("REFCGFS.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running REFCGFS.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)
        # --- REFCHLCY.py ---
        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/GFS/REFCHLCY.py"],
                check=True,
                cwd="/opt/render/project/src/GFS",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print("REFCHLCY.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running REFCHLCY.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)
        # --- tmp_surface.py ---
        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/GFS/tmp_surface.py"],
                check=True,
                cwd="/opt/render/project/src/GFS",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print("tmp_surface.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running tmp_surface.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)
        # --- vertical_velocity_500mb.py ---
        try:
            result = subprocess.run(
                ["python", "/opt/render/project/src/GFS/vertical_velocity_500mb.py"],
                check=True,
                cwd="/opt/render/project/src/GFS",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print("vertical_velocity_500mb.py ran successfully!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            error_trace = traceback.format_exc()
            print(f"Error running vertical_velocity_500mb.py:\n{error_trace}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)
    threading.Thread(target=run_gfs_scripts).start()
    return "All GFS scripts started sequentially in background!", 200

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

@app.route("/nbm_gust_pngs/<path:filename>")
def serve_nbm_gust_png(filename):
    # Serve the colorbar for colorbar.png requests
    if filename == "colorbar.png":
        return send_from_directory(COLORBAR_DIR, "GUST_colorbar.png")
    return api_serve_image(PNG_DIR_NBM_GUST, filename)

@app.route("/nbm_hail_pngs/<path:filename>")
def serve_nbm_hail_png(filename):
    # Serve the colorbar for colorbar.png requests
    if filename == "colorbar.png":
        return send_from_directory(os.path.join(BASE_DIR, "colorbars"), "HailProbability.png")
    return api_serve_image(PNG_DIR_NBM_HAIL, filename)

@app.route("/nbm_tornado_pngs/<path:filename>")
def serve_nbm_tornado_png(filename):
    # Serve the colorbar for colorbar.png requests
    if filename == "colorbar.png":
        return send_from_directory(os.path.join(BASE_DIR, "colorbars"), "tornado_colorbar.png")
    return api_serve_image(PNG_DIR_NBM_TORNADO, filename)

@app.route("/nbm_tstm_pngs/<path:filename>")
def serve_nbm_tstm_png(filename):
    # Serve the colorbar for colorbar.png requests
    if filename == "colorbar.png":
        return send_from_directory(os.path.join(BASE_DIR, "colorbars"), "Thunderstormcolorbar.png")
    return api_serve_image(PNG_DIR_NBM_TSTM, filename)

@app.route("/nbm_cape_pngs/<path:filename>")
def serve_nbm_cape_png(filename):
    # Serve the colorbar for colorbar.png requests
    if filename == "colorbar.png":
        return send_from_directory(os.path.join(BASE_DIR, "colorbars"), "CAPE_colorbar.png")
    return api_serve_image(PNG_DIR_NBM_CAPE, filename)

@app.route("/nbm_wind_pngs/<path:filename>")
def serve_nbm_wind_png(filename):
    # Serve the colorbar for colorbar.png requests
    if filename == "colorbar.png":
        # This must point to colorbars/WIND10M_colorbar.png
        return send_from_directory(COLORBAR_DIR, "WIND10M_colorbar.png")
    return api_serve_image(PNG_DIR_NBM_WIND, filename)

# Add GFS directory
PNG_DIR_GFS_REFCGFS = os.path.join(BASE_DIR, "GFS", "GFS", "static", "REFCGFS")
PNG_DIR_GFS_HGT500 = os.path.join(BASE_DIR, "GFS", "GFS", "static", "hgt_500")
PNG_DIR_GFS_ABSVORT = os.path.join(BASE_DIR, "GFS", "GFS", "static", "abs_vort")
PNG_DIR_GFS_MSLP = os.path.join(BASE_DIR, "GFS", "GFS", "static", "gfs_mslp_surface")
PNG_DIR_GFS_24HR = os.path.join(BASE_DIR, "GFS", "GFS", "static", "gfs_total_24_hour")
PNG_DIR_GFS_ACCUM = os.path.join(BASE_DIR, "GFS", "GFS", "static", "gfs_total_accum_precip")
PNG_DIR_GFS_TOTP = os.path.join(BASE_DIR, "GFS", "GFS", "static", "gfs_total_precip")
PNG_DIR_GFS_TMP2M = os.path.join(BASE_DIR, "GFS", "GFS", "static", "tmp_surface")
PNG_DIR_GFS_VERTICAL_VELOCITY = os.path.join(BASE_DIR, "GFS", "GFS", "static", "gfs_vertical_velocity_500mb")
# Add GFS convective precip accum directory
PNG_DIR_GFS_CONVECTIVE_ACCUM = os.path.join(BASE_DIR, "GFS", "GFS", "static", "gfs_convective_accum_precip")


import re

def extract_png_time(filename):
    # Try to extract a numeric timestamp or sequence from the filename
    # Example: sat_20240612_1200.png or 20240612_1200.png or sat_001.png
    m = re.search(r'(\d{8}_\d{4})', filename)  # e.g. 20240612_1200
    if m:
        # Convert to integer for sorting (YYYYMMDDHHMM)
        return int(m.group(1).replace('_', ''))
    m2 = re.search(r'(\d+)', filename)
    if m2:
        return int(m2.group(1))
    return 0

@app.route("/satellite_images")
def list_satellite_images():
    try:
        files = [f for f in os.listdir(SATELLITE_DIR) if f.lower().endswith(".png")]
        files.sort(key=extract_png_time)
        return jsonify(files)
    except Exception as e:
        return jsonify([])

@app.route("/satellite_images/<path:filename>")
def serve_satellite_image(filename):
    return send_from_directory(SATELLITE_DIR, filename)

@app.route("/ir_images")
def list_ir_images():
    try:
        files = [f for f in os.listdir(IR_DIR) if f.lower().endswith(".png")]
        files.sort(key=extract_png_time)
        return jsonify(files)
    except Exception as e:
        return jsonify([])

@app.route("/ir_images/<path:filename>")
def serve_ir_image(filename):
    return send_from_directory(IR_DIR, filename)

# --- Add radar endpoints below ---
@app.route("/radar_images")
def list_radar_images():
    try:
        files = [f for f in os.listdir(RADAR_DIR) if f.lower().endswith(".png")]
        files.sort(key=extract_png_time)
        return jsonify(files)
    except Exception as e:
        return jsonify([])

@app.route("/radar_images/<path:filename>")
def serve_radar_image(filename):
    return send_from_directory(RADAR_DIR, filename)

@app.route("/radar_ag_images")
def list_radar_ag_images():
    try:
        files = [f for f in os.listdir(RADAR_AVG_DIR) if f.lower().endswith(".png")]
        files.sort()
        return jsonify(files)
    except Exception as e:
        print(f"Error listing Radar/refcavg: {e}")
        return jsonify([])

@app.route("/radar_raw_images")
def list_radar_raw_images():
    try:
        files = [f for f in os.listdir(RADAR_RAW_DIR) if f.lower().endswith(".png")]
        files.sort()
        return jsonify(files)
    except Exception as e:
        print(f"Error listing Radar/refcraw: {e}")
        return jsonify([])

@app.route("/radar_ag/<path:filename>")
def serve_radar_ag(filename):
    # Securely serve files from Radar/refcavg
    return send_from_directory(RADAR_AVG_DIR, filename)

@app.route("/radar_raw/<path:filename>")
def serve_radar_raw(filename):
    # Securely serve files from Radar/refcraw
    return send_from_directory(RADAR_RAW_DIR, filename)

@app.route("/afd_summary_ALY.txt")
def serve_afd_summary_aly():
    afd_path = os.path.join(BASE_DIR, "weatherdata", "afd_summary_ALY.txt")
    if not os.path.isfile(afd_path):
        return "Summary not found.", 404
    return send_file(afd_path, mimetype="text/plain")

@app.route("/hrrr_archives")
def hrrr_archives():
    saved_dir = os.path.join(BASE_DIR, "HRRRSAVED")
    try:
        # List all directories in HRRRSAVED (no filter on _z or anything else)
        archives = [
            name for name in os.listdir(saved_dir)
            if os.path.isdir(os.path.join(saved_dir, name))
        ]
        archives.sort(reverse=True)
        return jsonify(archives)
    except Exception:
        return jsonify([])

# --- Serve archived PNGs for overlays ---
@app.route("/archive_pngs/<archive>/<overlay>/<path:filename>")
def serve_archive_png(archive, overlay, filename):
    # Defensive: only allow overlays that are valid
    allowed_overlays = {
        "REFC", "MSLP", "2mtemp", "lighting", "RH", "HAIL", "cape", "cin",
        "LCDC", "MCDC", "HCDC", "PRECIP", "WIND10M", "wind_bars_station",
        "HLCY", "PWAT", "GUST", "VUCSH_VVCSH"
    }
    # Normalize overlay for case-insensitive match
    overlay_norm = overlay.lower()
    # Map overlay to actual folder name (case-sensitive on some OS)
    overlay_map = {
        "refc": "REFC",
        "mslp": "MSLP",
        "temp2m": "2mtemp",
        "lightning": "lighting",
        "rh": "RH",
        "hail": "HAIL",
        "cape": "cape",
        "cin": "cin",
        "lcdc": "LCDC",
        "mcdc": "MCDC",
        "hcdc": "HCDC",
        "precip": "PRECIP",
        "wind10m": "WIND10M",
        "wind10m_station": "wind_bars_station",
        "srh": "HLCY",
        "pwat": "PWAT",
        "gust": "GUST",
        "shear_vector": "VUCSH_VVCSH"
    }
    # Use mapped overlay folder if present
    overlay_folder = overlay_map.get(overlay_norm, overlay)
    if overlay_folder not in allowed_overlays:
        return "Invalid overlay", 404
    archive_dir = os.path.join(BASE_DIR, "HRRRSAVED", archive, "static", overlay_folder)
    filename = filename.split('?', 1)[0]
    full_path = os.path.join(archive_dir, filename)
    print(f"Serving archive overlay: {full_path}")  # Debug log
    if not os.path.isfile(full_path):
        print(f"File NOT FOUND: {full_path}")
        return "Not found", 404
    return send_file(full_path)

@app.route("/archive_images/<archive>/<overlay>")
def list_archive_images(archive, overlay):
    archive_dir = os.path.join(BASE_DIR, "HRRRSAVED", archive, "static", overlay)
    try:
        files = [f for f in os.listdir(archive_dir) if f.lower().endswith(".png")]
        files.sort()
        return jsonify(files)
    except Exception as e:
        return jsonify([])

@app.route("/gfs_refcgfs_images")
def list_gfs_refcgfs_images():
    try:
        files = [f for f in os.listdir(PNG_DIR_GFS_REFCGFS) if f.lower().endswith(".png")]
        files.sort()
        return jsonify(files)
    except Exception as e:
        return jsonify([])

@app.route("/gfs_refcgfs_pngs/<path:filename>")
def serve_gfs_refcgfs_png(filename):
    # Serve the GFS reflectivity colorbar for colorbar.png requests
    if filename == "colorbar.png":
        return send_from_directory(COLORBAR_DIR, "GFSreflectivity.png")
    return send_from_directory(PNG_DIR_GFS_REFCGFS, filename)

@app.route("/gfs_hgt500_images")
def list_gfs_hgt500_images():
    try:
        files = [f for f in os.listdir(PNG_DIR_GFS_HGT500) if f.lower().endswith(".png")]
        files.sort()
        return jsonify(files)
    except Exception as e:
        return jsonify([])

@app.route("/gfs_hgt500_pngs/<path:filename>")
def serve_gfs_hgt500_png(filename):
    return send_from_directory(PNG_DIR_GFS_HGT500, filename)

@app.route("/gfs_absvort_images")
def list_gfs_absvort_images():
    try:
        files = [f for f in os.listdir(PNG_DIR_GFS_ABSVORT) if f.lower().endswith(".png")]
        files.sort()
        return jsonify(files)
    except Exception as e:
        return jsonify([])

@app.route("/gfs_absvort_pngs/<path:filename>")
def serve_gfs_absvort_png(filename):
    return send_from_directory(PNG_DIR_GFS_ABSVORT, filename)

@app.route("/gfs_mslp_images")
def list_gfs_mslp_images():
    try:
        files = [f for f in os.listdir(PNG_DIR_GFS_MSLP) if f.lower().endswith(".png")]
        files.sort()
        return jsonify(files)
    except Exception as e:
        return jsonify([])

@app.route("/gfs_mslp_pngs/<path:filename>")
def serve_gfs_mslp_png(filename):
    return send_from_directory(PNG_DIR_GFS_MSLP, filename)

@app.route("/gfs_24hr_images")
def list_gfs_24hr_images():
    try:
        files = [f for f in os.listdir(PNG_DIR_GFS_24HR) if f.lower().endswith(".png")]
        files.sort()
        return jsonify(files)
    except Exception as e:
        return jsonify([])

@app.route("/gfs_24hr_pngs/<path:filename>")
def serve_gfs_24hr_png(filename):
    return send_from_directory(PNG_DIR_GFS_24HR, filename)

@app.route("/gfs_accum_images")
def list_gfs_accum_images():
    try:
        files = [f for f in os.listdir(PNG_DIR_GFS_ACCUM) if f.lower().endswith(".png")]
        files.sort()
        return jsonify(files)
    except Exception as e:
        return jsonify([])

@app.route("/gfs_accum_pngs/<path:filename>")
def serve_gfs_accum_png(filename):
    return send_from_directory(PNG_DIR_GFS_ACCUM, filename)

@app.route("/gfs_totp_images")
def list_gfs_totp_images():
    try:
        files = [f for f in os.listdir(PNG_DIR_GFS_TOTP) if f.lower().endswith(".png")]
        files.sort()
        return jsonify(files)
    except Exception as e:
        return jsonify([])

@app.route("/gfs_totp_pngs/<path:filename>")
def serve_gfs_totp_png(filename):
    return send_from_directory(PNG_DIR_GFS_TOTP, filename)

@app.route("/gfs_tmp2m_images")
def list_gfs_tmp2m_images():
    try:
        files = [f for f in os.listdir(PNG_DIR_GFS_TMP2M) if f.lower().endswith(".png")]
        files.sort()
        return jsonify(files)
    except Exception as e:
        return jsonify([])

@app.route("/gfs_tmp2m_pngs/<path:filename>")
def serve_gfs_tmp2m_png(filename):
    return send_from_directory(PNG_DIR_GFS_TMP2M, filename)

# Add GFS REFCHLCY directory
PNG_DIR_GFS_REFCHLCY = os.path.join(BASE_DIR, "GFS", "GFS", "static", "REFCHLCY")

@app.route("/gfs_refchlcy_images")
def list_gfs_refchlcy_images():
    try:
        files = [f for f in os.listdir(PNG_DIR_GFS_REFCHLCY) if f.lower().endswith(".png")]
        files.sort()
        return jsonify(files)
    except Exception as e:
        return jsonify([])

@app.route("/gfs_refchlcy_pngs/<path:filename>")
def serve_gfs_refchlcy_png(filename):
    # Serve the GFS REFCHLCY colorbar for colorbar.png requests
    if filename == "colorbar.png":
        return send_from_directory(COLORBAR_DIR, "GFSREFCHLCY_colorbar.png")
    return send_from_directory(PNG_DIR_GFS_REFCHLCY, filename)

# Add GFS HAINESCY directory
PNG_DIR_GFS_HAINESCY = os.path.join(BASE_DIR, "GFS", "GFS", "static", "HAINESCY")

@app.route("/gfs_hainesc_images")
def list_gfs_hainesc_images():
    try:
        files = [f for f in os.listdir(PNG_DIR_GFS_HAINESCY) if f.lower().endswith(".png")]
        files.sort()
        return jsonify(files)
    except Exception as e:
        return jsonify([])

@app.route("/gfs_hainesc_pngs/<path:filename>")
def serve_gfs_hainesc_png(filename):
    # Serve the GFS Haines Index colorbar for colorbar.png requests
    if filename == "colorbar.png":
        return send_from_directory(COLORBAR_DIR, "GFS_haines_colorbar.png")
    # Ensure the correct directory is used for serving Haines Index images
    return api_serve_image(PNG_DIR_GFS_HAINESCY, filename)

@app.route("/gfs_vertical_velocity_images")
def list_gfs_vertical_velocity_images():
    try:
        files = [f for f in os.listdir(PNG_DIR_GFS_VERTICAL_VELOCITY) if f.lower().endswith(".png")]
        files.sort()
        return jsonify(files)
    except Exception as e:
        return jsonify([])

@app.route("/gfs_vertical_velocity_pngs/<path:filename>")
def serve_gfs_vertical_velocity_png(filename):
    # Serve the GFS Vertical Velocity colorbar for colorbar.png requests
    if filename == "colorbar.png":
        return send_from_directory(COLORBAR_DIR, "GFS_Vertical_vs.png")
    return send_from_directory(PNG_DIR_GFS_VERTICAL_VELOCITY, filename)

@app.route("/gfs_convective_accum_images")
def list_gfs_convective_accum_images():
    try:
        files = [f for f in os.listdir(PNG_DIR_GFS_CONVECTIVE_ACCUM) if f.lower().endswith(".png")]
        files.sort()
        return jsonify(files)
    except Exception as e:
        return jsonify([])

@app.route("/gfs_convective_accum_pngs/<path:filename>")
def serve_gfs_convective_accum_png(filename):
    return send_from_directory(PNG_DIR_GFS_CONVECTIVE_ACCUM, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
