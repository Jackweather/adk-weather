import os
import requests
from datetime import datetime, timedelta
import xarray as xr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, BoundaryNorm
import numpy as np
import cartopy.crs as ccrs
import matplotlib.patheffects as path_effects
import time
import gc

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Clean up old files in grib_files, pngs, and REFCGFS directories ---
for folder in [
    os.path.join(BASE_DIR, "GFS", "static", "REFCGFS", "grib_files"),
    os.path.join(BASE_DIR, "GFS", "static", "pngs"),
    os.path.join(BASE_DIR, "GFS", "static", "REFCGFS")
]:
    if os.path.exists(folder):
        for f in os.listdir(folder):
            file_path = os.path.join(folder, f)
            if os.path.isfile(file_path):
                os.remove(file_path)

# Directories
output_dir = os.path.join(BASE_DIR, "GFS")
refc_dir = os.path.join(output_dir, "static", "REFCGFS")
grib_dir = os.path.join(refc_dir, "grib_files")
png_dir = refc_dir
os.makedirs(grib_dir, exist_ok=True)
os.makedirs(png_dir, exist_ok=True)

# GFS 0.25-degree URL and variable
base_url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"
variable_refc = "REFC"
# Current UTC time minus 6 hours (nearest available GFS cycle)
current_utc_time = datetime.utcnow() - timedelta(hours=6)
date_str = current_utc_time.strftime("%Y%m%d")
hour_str = str(current_utc_time.hour // 6 * 6).zfill(2)  # nearest 6-hour slot

# Custom colormap and levels for reflectivity (dBZ)
# NWS style levels and colors
refc_levels = [10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60]
refc_colors = [
    "#00ff00",  # 10: green
    "#33cc00",  # 15: dark green
    "#ffff00",  # 20: yellow
    "#ffcc00",  # 25: gold
    "#ff9900",  # 30: orange
    "#ff0000",  # 35: red
    "#cc0000",  # 40: dark red
    "#990099",  # 45: purple
    "#c800ff",  # 50: magenta
    "#ff00ff",  # 55: pink
    "#ffffff",  # 60: white
]
refc_cmap = LinearSegmentedColormap.from_list("refc_custom", refc_colors, N=len(refc_colors))

# Function to download GRIB files (GFS REFC)
def download_file(hour_str, step):
    if step == 0:
        file_name = f"gfs.t{hour_str}z.pgrb2.0p25.f000"
    else:
        file_name = f"gfs.t{hour_str}z.pgrb2.0p25.f{step:03d}"
    file_path = os.path.join(grib_dir, file_name)
    url_refc = (
        f"{base_url}?file={file_name}"
        f"&lev_entire_atmosphere=on&var_{variable_refc}=on"
        f"&subregion=&leftlon=220&rightlon=300&toplat=55&bottomlat=20"
        f"&dir=%2Fgfs.{date_str}%2F{hour_str}%2Fatmos"
    )
    response = requests.get(url_refc, stream=True)
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
    ds = xr.open_dataset(file_path, engine="cfgrib")
    # GFS composite reflectivity is usually 'refc'
    data = ds['refc'].values  # dBZ

    # Make 0 dBZ transparent
    data = np.where(data == 0, np.nan, data)

    fig = plt.figure(figsize=(10, 7), dpi=600)
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([-126, -69, 24, 50], crs=ccrs.PlateCarree())

    if 'latitude' in ds and 'longitude' in ds:
        lats = ds['latitude'].values
        lons = ds['longitude'].values
        lons_plot = np.where(lons > 180, lons - 360, lons)
        # Ensure lats, lons, and data are 2D for contourf
        if lats.ndim == 1 and lons.ndim == 1:
            Lon2d, Lat2d = np.meshgrid(lons_plot, lats)
            data2d = data.squeeze()
        else:
            Lon2d, Lat2d = lons_plot, lats
            data2d = data.squeeze()
        mesh = ax.contourf(
            Lon2d, Lat2d, data2d,
            levels=refc_levels,
            cmap=refc_cmap,
            extend='max',
            transform=ccrs.PlateCarree()
        )
    else:
        leaflet_extent = [-126, -69, 24, 50]
        mesh = ax.imshow(
            data.squeeze(),
            cmap=refc_cmap,
            extent=leaflet_extent,
            origin='lower',
            interpolation='bilinear',
            aspect='auto',
            transform=ccrs.PlateCarree()
        )
    # Remove colorbar (do not add it)
    # Remove axes
    ax.set_axis_off()
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    png_path = os.path.join(png_dir, f"refc_{step:03d}.png")
    plt.savefig(png_path, bbox_inches='tight', pad_inches=0, transparent=True, dpi=600)
    plt.close(fig)
    print(f"Generated clean PNG: {png_path}")
    return png_path

# Main process: Download and plot
grib_files = []
png_files = []
forecast_steps = [0] + list(range(6, 385, 6))  # include analysis step 0
if 264 not in forecast_steps:
    forecast_steps.append(264)
for step in forecast_steps:
    grib_file = download_file(hour_str, step)
    if grib_file:
        grib_files.append(grib_file)
        png_file = generate_clean_png(grib_file, step)
        png_files.append(png_file)
        gc.collect()
        time.sleep(3)

print("All GRIB file download and PNG creation tasks complete!")
forecast_steps = [0] + list(range(6, 385, 6))  # include analysis step 0
if 264 not in forecast_steps:
    forecast_steps.append(264)
for step in forecast_steps:
    grib_file = download_file(hour_str, step)
    if grib_file:
        grib_files.append(grib_file)
        png_file = generate_clean_png(grib_file, step)
        png_files.append(png_file)
        gc.collect()
        time.sleep(3)

        print("All GRIB file download and PNG creation tasks complete!")
        gc.collect()
        time.sleep(3)
