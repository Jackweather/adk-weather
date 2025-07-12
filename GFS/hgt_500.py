import os
import requests
from datetime import datetime, timedelta
import xarray as xr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import cartopy.crs as ccrs
import matplotlib.patheffects as path_effects
import time
import gc

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Clean up old files in grib_files, pngs, and hgt_500 directories ---
for folder in [
    os.path.join(BASE_DIR, "GFS", "static", "hgt_500", "grib_files"),
    os.path.join(BASE_DIR, "GFS", "static", "pngs"),
    os.path.join(BASE_DIR, "GFS", "static", "hgt_500")
]:
    if os.path.exists(folder):
        for f in os.listdir(folder):
            file_path = os.path.join(folder, f)
            if os.path.isfile(file_path):
                os.remove(file_path)

# Directories
output_dir = os.path.join(BASE_DIR, "GFS")
hgt_500_dir = os.path.join(output_dir, "static", "hgt_500")
grib_dir = os.path.join(hgt_500_dir, "grib_files")
png_dir = hgt_500_dir  # Save PNGs directly in hgt_500_dir
os.makedirs(grib_dir, exist_ok=True)
os.makedirs(png_dir, exist_ok=True)

# GFS NOMADS URL and variable for 500mb height
base_url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_1p00.pl"
variable_hgt = "HGT"
level = "500_mb"
# Current UTC time minus 6 hours (nearest available GFS cycle)
current_utc_time = datetime.utcnow() - timedelta(hours=6)
date_str = current_utc_time.strftime("%Y%m%d")
hour_str = str(current_utc_time.hour // 6 * 6).zfill(2)  # nearest 6-hour slot

# Custom colormap and levels for 500mb height (meters)
# Use a more "colorful" (higher contrast) blue-to-red colormap for trough/ridge distinction
hgt_levels = np.arange(4800, 6000+1, 20)  # 4800 to 6000 by 30 meters
custom_cmap = LinearSegmentedColormap.from_list(
    "hgt_cmap",
    [
        "#0d0887",  # 4800 m: deep purple/blue (very low heights, strong trough)
        "#2a0593",  # 4920 m: blue-violet
        "#2b83ba",  # 5040 m: blue
        "#43e0f7",  # 5160 m: cyan
        "#abff4f",  # 5280 m: green-yellow
        "#ffffbf",  # 5400 m: yellow (neutral)
        "#a2b91d",  # 5520 m: yellow-green/orange
        "#f1da05",  # 5640 m: yellow-orange
        "#cf4217",  # 5760 m: red-orange
        "#e70a0a",  # 5880 m: deep red (extreme ridge)
    ],
    N=256
)
# Color value mapping (approximate, for 4800-6000 by 20m steps):
# 4800 m: #0d0887
# 4920 m: #2a0593
# 5040 m: #2b83ba
# 5160 m: #43e0f7
# 5280 m: #abff4f
# 5400 m: #ffffbf
# 5520 m: #a2b91d
# 5640 m: #dad616
# 5760 m: #e43c09
# 5880 m: #e70a0a
# (Colors are interpolated between these values for intermediate heights.)

# Function to download GRIB files (GFS 500mb height)
def download_file(hour_str, step):
    file_name = f"gfs.t{hour_str}z.pgrb2.1p00.f{step:03d}"
    file_path = os.path.join(grib_dir, file_name)
    url_hgt = (
        f"{base_url}?file={file_name}"
        f"&lev_{level}=on&var_{variable_hgt}=on"
        f"&subregion=&leftlon=220&rightlon=300&toplat=55&bottomlat=20"
        f"&dir=%2Fgfs.{date_str}%2F{hour_str}%2Fatmos"
    )
    response = requests.get(url_hgt, stream=True)
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
    data = ds['gh'].values  # meters

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
        # Filled contours for color
        mesh = ax.contourf(
            Lon2d, Lat2d, data2d,
            levels=hgt_levels,
            cmap=custom_cmap,
            extend='both',
            alpha=0.85,  # slightly transparent for overlay
            antialiased=True,
            transform=ccrs.PlateCarree()
        )
        # Add black contour lines for every 120m to highlight ridges/troughs
        contour_lines = ax.contour(
            Lon2d, Lat2d, data2d,
            levels=np.arange(4800, 6000+1, 120),
            colors='black',
            linewidths=0.5,
            linestyles='solid',
            alpha=0.7,
            transform=ccrs.PlateCarree()
        )
    else:
        leaflet_extent = [-126, -69, 24, 50]
        mesh = ax.imshow(
            data.squeeze(),
            cmap=custom_cmap,
            extent=leaflet_extent,
            origin='lower',
            interpolation='bilinear',
            aspect='auto',
            alpha=0.85,
            transform=ccrs.PlateCarree()
        )
    ax.set_axis_off()
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    png_path = os.path.join(png_dir, f"hgt500_{step:03d}.png")
    plt.savefig(png_path, bbox_inches='tight', pad_inches=0, transparent=True, dpi=600)
    plt.close(fig)
    print(f"Generated clean PNG: {png_path}")
    return png_path

# Main process: Download and plot
grib_files = []
png_files = []
forecast_steps = list(range(6, 385, 6))  # 6, 12, ..., 384
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
print("All GRIB file download and PNG creation tasks complete!")
