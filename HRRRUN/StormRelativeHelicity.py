import os
import requests
from datetime import datetime, timedelta
import xarray as xr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
import cartopy.crs as ccrs
import time
import gc
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Clean up old files in grib_files and pngs directories ---
for folder in [
    os.path.join(BASE_DIR, "Hrrr", "static", "HLCY", "grib_files"),
    os.path.join(BASE_DIR, "Hrrr", "static", "HLCY")
]:
    if os.path.exists(folder):
        for f in os.listdir(folder):
            file_path = os.path.join(folder, f)
            if os.path.isfile(file_path):
                os.remove(file_path)

# Directories
base_url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl"
output_dir = os.path.join(BASE_DIR, "Hrrr")
hlcy_dir = os.path.join(output_dir, "static", "HLCY")
grib_dir = os.path.join(hlcy_dir, "grib_files")
os.makedirs(grib_dir, exist_ok=True)
os.makedirs(hlcy_dir, exist_ok=True)

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

# HLCY variable and colormap
variable_hlcy = "HLCY"
colors = ['white'] + [plt.cm.YlOrRd(i) for i in range(1, 256)]
cmap = ListedColormap(colors)
bounds = list(np.linspace(0, 800, 256))
norm = BoundaryNorm(bounds, cmap.N)

# Function to download GRIB files
def download_file(hour_str, step):
    file_name = f"hrrr.t{hour_str}z.wrfsfcf{step:02d}.grib2"
    file_path = os.path.join(grib_dir, file_name)
    url_hlcy = (f"{base_url}?dir=%2Fhrrr.{date_str}%2Fconus&file={file_name}"
                f"&var_{variable_hlcy}=on&lev_3000-0_m_above_ground=on")
    response = requests.get(url_hlcy, stream=True)
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

# Function to generate a clean PNG from GRIB file (with Cartopy projection) using xarray
def generate_clean_png(file_path, step):
    ds = xr.open_dataset(file_path, engine="cfgrib")
    # Try to get the variable name (could be 'hlcy' or 'HLCY')
    varname = None
    for v in ds.data_vars:
        if v.lower().startswith('hlcy'):
            varname = v
            break
    if varname is None:
        raise RuntimeError("No HLCY variable found in GRIB file")
    hlcy = ds[varname]
    # Only positive values
    hlcy_positive = hlcy.where(hlcy > 99)
    lats = ds['latitude']
    lons = ds['longitude']
    fig = plt.figure(figsize=(10, 7), dpi=850)
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([-126, -69, 24, 50], crs=ccrs.PlateCarree())
    # Contour lines with color mapping: stronger values = warmer colors (red/orange/yellow)
    levels = [50, 100, 200, 300, 400, 500, 600, 700, 800]
    cmap_lines = plt.get_cmap('YlOrRd', len(levels))
    contour = ax.contour(
        lons, lats, hlcy_positive.squeeze(),
        levels=levels, cmap=cmap_lines, linewidths=0.7, transform=ccrs.PlateCarree()
    )
    # Remove fontweight (not supported), use only supported arguments
    ax.clabel(contour, inline=True, fontsize=2, fmt='%d', colors='black')
    ax.set_axis_off()
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    png_path = os.path.join(hlcy_dir, f"HLCY_{step:02d}.png")
    plt.savefig(png_path, bbox_inches='tight', pad_inches=0, transparent=True)
    plt.close(fig)
    print(f"Generated clean PNG: {png_path}")
    return png_path

# Main process: Download and plot
grib_files = []
png_files = []
for step in range(0, 49):  # Loop through forecast steps (00 to 48 hours)
    grib_file = download_file(hour_str, step)
    if grib_file:
        grib_files.append(grib_file)
        png_file = generate_clean_png(grib_file, step)
        png_files.append(png_file)
        gc.collect()
        time.sleep(3)

print("All GRIB file download and PNG creation tasks complete!")
