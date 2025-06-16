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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Clean up old files in grib_files and MAXREF directories ---
for folder in [
    os.path.join(BASE_DIR, "NBM", "static", "MAXREF", "grib_files"),
    os.path.join(BASE_DIR, "NBM", "static", "MAXREF")
]:
    if os.path.exists(folder):
        for f in os.listdir(folder):
            file_path = os.path.join(folder, f)
            if os.path.isfile(file_path):
                os.remove(file_path)

# Directories
base_url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_blend.pl"
output_dir = os.path.join(BASE_DIR, "NBM")
maxref_dir = os.path.join(output_dir, "static", "MAXREF")
grib_dir = os.path.join(maxref_dir, "grib_files")
os.makedirs(grib_dir, exist_ok=True)
os.makedirs(maxref_dir, exist_ok=True)

# Get the current UTC date and time and select the most recent NBM run (0z, 6z, 12z, 18z)
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

# MAXREF variable and colormap (same as REFC)
variable_maxref = "MAXREF"
colors = [
    "#00000000", "#04e9e7", "#019ff4", "#0300f4", "#02fd02",
    "#01c501", "#008e00", "#fdf802", "#e5bc00", "#fd9500",
    "#fd0000", "#d40000", "#bc0000", "#f800fd", "#9854c6", "#fdfdfd"
]
bounds = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75]
cmap = ListedColormap(colors)
norm = BoundaryNorm(bounds, cmap.N)

# Function to download GRIB files
def download_file(hour_str, step):
    file_name = f"blend.t{hour_str}z.core.f{step:03d}.co.grib2"
    file_path = os.path.join(grib_dir, file_name)
    url_maxref = (
        f"{base_url}?dir=%2Fblend.{date_str}%2F{hour_str}%2Fcore&file={file_name}"
        f"&var_{variable_maxref}=on&lev_1000_m_above_ground=on"
    )
    response = requests.get(url_maxref, stream=True)
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

# Function to generate a clean PNG from GRIB file (with Cartopy projection)
def generate_clean_png(file_path, step):
    ds = xr.open_dataset(file_path, engine="cfgrib")
    # Try to get the correct variable name for MAXREF
    var_name = None
    for v in ds.variables:
        if v.lower() == "maxref":
            var_name = v
            break
    if var_name is None:
        if "unknown" in ds.variables:
            var_name = "unknown"
        else:
            raise KeyError("No suitable MAXREF variable found in the dataset.")
    maxref = ds[var_name].where((ds[var_name] >= 0) & (ds[var_name] <= 75))
    lats = ds['latitude']
    lons = ds['longitude']
    fig = plt.figure(figsize=(10, 7), dpi=850)
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([-126, -69, 24, 50], crs=ccrs.PlateCarree())
    # Use contourf for smoother, filled contours
    contour = ax.contourf(
        lons, lats, maxref.squeeze(),
        levels=bounds, cmap=cmap, norm=norm, transform=ccrs.PlateCarree(), extend='max'
    )
    ax.set_axis_off()
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    png_path = os.path.join(maxref_dir, f"MAXREF_{step:03d}.png")
    plt.savefig(png_path, bbox_inches='tight', pad_inches=0, transparent=True)
    plt.close(fig)
    print(f"Generated clean PNG: {png_path}")
    return png_path

# Main process: Download and plot
grib_files = []
png_files = []
failed_downloads = 0  # Track failed downloads

for step in range(6, 37, 6):  # Loop through forecast steps (6, 12, ..., 264)
    grib_file = download_file(hour_str, step)
    if grib_file:
        grib_files.append(grib_file)
        png_file = generate_clean_png(grib_file, step)
        png_files.append(png_file)
        gc.collect()
        time.sleep(3)
    else:
        failed_downloads += 1
        if failed_downloads >= 5:
            print("Encountered 5 failed downloads. Exiting.")
            exit(1)

print("All GRIB file download and PNG creation tasks complete!")
