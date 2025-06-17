import os
import requests
from datetime import datetime, timedelta
import xarray as xr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
import numpy as np
import cartopy.crs as ccrs
import matplotlib.patheffects as path_effects
import time
import gc

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Clean up old files in grib_files and tornado directories ---
for folder in [
    os.path.join(BASE_DIR, "NBM", "static", "tornado", "grib_files"),
    os.path.join(BASE_DIR, "NBM", "static", "tornado")
]:
    if os.path.exists(folder):
        for f in os.listdir(folder):
            file_path = os.path.join(folder, f)
            if os.path.isfile(file_path):
                os.remove(file_path)

# Directories
base_url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_blend.pl"
output_dir = os.path.join(BASE_DIR, "NBM")
tornado_dir = os.path.join(output_dir, "static", "tornado")
grib_dir = os.path.join(tornado_dir, "grib_files")
png_dir = tornado_dir
os.makedirs(grib_dir, exist_ok=True)
os.makedirs(png_dir, exist_ok=True)

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
hour_str = str(run_hour).zfill(2)

variable_tornado = "TORPROB"
level = "surface"

# Tornado probability color scale (0-100%)
colors = [
    (1, 1, 1, 0),    # 0% (clear/transparent)
    "#cce6ff",        # 0-5% (very light blue)
    "#99ccff",        # 5-10% (light blue)
    "#66b3ff",        # 10-20% (blue)
    "#33cc33",        # 20-30% (green)
    "#ffff66",        # 30-40% (yellow)
    "#ffcc00",        # 40-50% (orange)
    "#ff6600",        # 50-60% (red-orange)
    "#ff0000",        # 60-70% (red)
    "#990099",        # 70-80% (purple)
    "#808080",        # 80-100% (gray)
]
bounds = [0, 1, 5, 10, 20, 30, 40, 50, 60, 70, 80, 100]
cmap = ListedColormap(colors)
norm = BoundaryNorm(bounds, cmap.N)

# Station list (same as gust)
GUST_STATIONS = [
    # ...existing station list from NBM_GUST.py...
    # (copy the full list here)
]

# Function to download GRIB files (NBM blend)
def download_file(hour_str, step):
    file_name = f"blend.t{hour_str}z.core.f{step:03d}.co.grib2"
    file_path = os.path.join(grib_dir, file_name)
    url_tornado = (f"{base_url}?dir=%2Fblend.{date_str}%2F{hour_str}%2Fcore&file={file_name}"
                   f"&var_{variable_tornado}=on&lev_{level}=on")
    response = requests.get(url_tornado, stream=True)
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

# Function to generate a clean PNG from GRIB file (no map features)
def generate_clean_png(file_path, step):
    ds = xr.open_dataset(file_path, engine="cfgrib", indexpath='')  # Prevents .idx file creation
    tornadoprob = ds['torprob']  # 0-100 (%)
    tornadoprob = tornadoprob.where((tornadoprob >= 0) & (tornadoprob <= 100))
    lats = ds['latitude'].values
    lons = ds['longitude'].values
    lons_plot = np.where(lons > 180, lons - 360, lons)

    fig = plt.figure(figsize=(10, 7), dpi=600)
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([-126, -69, 24, 50], crs=ccrs.PlateCarree())

    mesh = ax.pcolormesh(
        lons_plot, lats, tornadoprob.squeeze(),
        cmap=cmap,
        norm=norm,
        shading='auto',
        transform=ccrs.PlateCarree()
    )
    # Plot tornado probability values at station locations
    for stn_id, stn_name, stn_lat, stn_lon in GUST_STATIONS:
        stn_lon_grid = stn_lon if stn_lon >= 0 else stn_lon + 360
        if lats.ndim == 2 and lons.ndim == 2:
            dist = (lats - stn_lat) ** 2 + (lons - stn_lon_grid) ** 2
            iy, ix = np.unravel_index(np.argmin(dist), dist.shape)
        else:
            iy = np.abs(lats - stn_lat).argmin()
            ix = np.abs(lons - stn_lon_grid).argmin()
        tornado_val = tornadoprob.squeeze()[iy, ix]
        txt = ax.text(
            stn_lon, stn_lat, f"{tornado_val:.0f}",
            color='white', fontsize=1, fontweight='bold', fontname='DejaVu Sans',
            ha='center', va='center', transform=ccrs.PlateCarree(),
            zorder=2
        )
        txt.set_path_effects([
            path_effects.Stroke(linewidth=0.5, foreground='black'),
            path_effects.Normal()
        ])
    ax.set_axis_off()
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    png_path = os.path.join(png_dir, f"tornado_{step:03d}.png")
    plt.savefig(png_path, bbox_inches='tight', pad_inches=0, transparent=True, dpi=600)
    plt.close(fig)
    print(f"Generated clean PNG: {png_path}")
    return png_path

# Main process: Download and plot
grib_files = []
png_files = []
forecast_steps = list(range(6, 37, 6))
for step in forecast_steps:
    grib_file = download_file(hour_str, step)
    if grib_file:
        grib_files.append(grib_file)
        png_file = generate_clean_png(grib_file, step)
        png_files.append(png_file)
        gc.collect()
        time.sleep(3)

print("All NBM TORNADO GRIB file download and PNG creation tasks complete!")
