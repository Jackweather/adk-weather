import os
import requests
from datetime import datetime, timedelta
import xarray as xr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import numpy as np
from matplotlib.colors import ListedColormap, BoundaryNorm
import matplotlib.patches as mpatches

# --- Clean up old files in grib_files and pngs directories ---
hail_dir = os.path.join("Hrrr", "static", "HAIL")
grib_dir = os.path.join(hail_dir, "grib_files")
os.makedirs(grib_dir, exist_ok=True)
os.makedirs(hail_dir, exist_ok=True)
for folder in [grib_dir, hail_dir]:
    if os.path.exists(folder):
        for f in os.listdir(folder):
            file_path = os.path.join(folder, f)
            if os.path.isfile(file_path):
                os.remove(file_path)

# Get the current UTC date and time and select the most recent HRRR run (0z, 6z, 12z, 18z)
current_utc_time = datetime.utcnow()
run_hour = (current_utc_time.hour // 6) * 6
if run_hour == 24:
    run_hour = 18
date_for_run = current_utc_time
if current_utc_time.hour < run_hour:
    date_for_run = current_utc_time - timedelta(hours=6)
    run_hour = (date_for_run.hour // 6) * 6
date_str = date_for_run.strftime("%Y%m%d")
hour_str = str(run_hour).zfill(2)  # 00, 06, 12, 18

base_url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl"

def download_file(hour_str, step):
    file_name = f"hrrr.t{hour_str}z.wrfsfcf{step:02d}.grib2"
    file_path = os.path.join(grib_dir, file_name)
    url = (
        f"{base_url}?dir=%2Fhrrr.{date_str}%2Fconus"
        f"&file={file_name}"
        f"&var_HAIL=on"
        f"&lev_0.1_sigma_level=on"
        f"&lev_entire_atmosphere=on"
    )
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        print(f"Downloaded {file_name}")
        return file_path
    else:
        print(f"Failed to download {file_name} (Status Code: {response.status_code})")
        return None

def plot_hail_risk(filepath, save_path=None):
    try:
        print(f"📂 Reading GRIB2 file: {filepath}")
        ds = xr.open_dataset(filepath, engine="cfgrib", filter_by_keys={'typeOfLevel': 'sigma'})
        # Try to get the variable name for hail (case-insensitive)
        hail_var = None
        for v in ds.data_vars:
            if v.lower() == "hail":
                hail_var = v
                break
        if hail_var is None:
            raise Exception("No 'HAIL' variable found in GRIB2 file.")
        hail_vals_m = ds[hail_var].values
        lats = ds['latitude'].values
        lons = ds['longitude'].values

        # Convert meters to inches
        hail_vals = hail_vals_m * 39.3701

        # Define refined risk thresholds (in inches), excluding "No Risk"
        bins = [0.3, 0.75, 1.25, 1.75, 2.25, np.inf]
        risk_labels = [
            'Very Low Risk (0.30–0.50 in)',
            'Low Risk (0.50–1.00 in)',
            'Moderate Risk (1.00–1.75 in)',
            'High Risk (1.75–2.25 in)',
            'Extreme Risk (≥2.25 in)'
        ]
        colors = [
            '#d0f0fd',  # very light blue
            '#a6cee3',  # light blue
            '#1f78b4',  # blue
            '#b10026',  # red
            '#800026'   # dark red 
        ]

        # Digitize hail values into risk bins
        hail_risk = np.digitize(hail_vals, bins)

        # Mask areas below 0.3 inches (i.e., value 0 from digitize)
        hail_risk_masked = np.ma.masked_where(hail_risk == 0, hail_risk)

        # Adjust color map and normalization
        cmap = ListedColormap(colors)
        norm = BoundaryNorm(boundaries=[1, 2, 3, 4, 5, 6], ncolors=len(colors))

        # Plot setup
        plt.figure(figsize=(10, 7), dpi=850)
        ax = plt.axes(projection=ccrs.PlateCarree())
        ax.set_axis_off()
        plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
        ax.set_extent([-125, -66.5, 24, 50], crs=ccrs.PlateCarree())

        # Only plot hail risk, no map features or legend
        hail_plot = ax.pcolormesh(lons, lats, hail_risk_masked, cmap=cmap, norm=norm, transform=ccrs.PlateCarree())

        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            plt.savefig(save_path, bbox_inches='tight', pad_inches=0, transparent=True)
            print(f"✅ Plot saved to {save_path}")
        plt.close()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    for step in range(0, 49):  # 00 to 48 hours
        grib_file = download_file(hour_str, step)
        if grib_file:
            png_file = os.path.join(hail_dir, f"HAIL_{step:02d}.png")
            plot_hail_risk(filepath=grib_file, save_path=png_file)
    print("All HAIL GRIB file download and PNG creation tasks complete!")
