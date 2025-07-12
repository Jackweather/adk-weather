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

# --- Clean up old files in grib_files, pngs, and vertical_velocity_500mb directories ---
for folder in [
    os.path.join(BASE_DIR, "GFS", "static", "gfs_vertical_velocity_500mb", "grib_files"),
    os.path.join(BASE_DIR, "GFS", "static", "pngs"),
    os.path.join(BASE_DIR, "GFS", "static", "gfs_vertical_velocity_500mb")
]:
    if os.path.exists(folder):
        for f in os.listdir(folder):
            file_path = os.path.join(folder, f)
            if os.path.isfile(file_path):
                os.remove(file_path)

# Directories
output_dir = os.path.join(BASE_DIR, "GFS")
vertical_velocity_dir = os.path.join(output_dir, "static", "gfs_vertical_velocity_500mb")
grib_dir = os.path.join(vertical_velocity_dir, "grib_files")
png_dir = vertical_velocity_dir
os.makedirs(grib_dir, exist_ok=True)
os.makedirs(png_dir, exist_ok=True)

# GFS 0.25° NOMADS URL and variable
base_url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"
variable_dzdt = "DZDT"
level_500mb = "500_mb"
# Current UTC time minus 6 hours (nearest available GFS cycle)
current_utc_time = datetime.utcnow() - timedelta(hours=6)
date_str = current_utc_time.strftime("%Y%m%d")
hour_str = str(current_utc_time.hour // 6 * 6).zfill(2)  # nearest 6-hour slot

# Custom colormap and levels for vertical velocity (Pa/s)
dzdt_levels = np.arange(-1.0, 1.1, 0.1)  # -1.0 to 1.0 Pa/s, every 0.1 Pa/s
custom_cmap = LinearSegmentedColormap.from_list(
    "dzdt_cmap",
    [
        "#08306b", "#2171b5", "#6baed6", "#b3cde3", "#ffffff",
        "#fdd0a2", "#fd8d3c", "#e6550d", "#a63603"
    ],
    N=256
)

# Function to download GRIB files (GFS 0.25°)
def download_file(hour_str, step):
    file_name = f"gfs.t{hour_str}z.pgrb2.0p25.f{step:03d}"
    file_path = os.path.join(grib_dir, file_name)
    url_dzdt = (
        f"{base_url}?file={file_name}"
        f"&lev_{level_500mb}=on&var_{variable_dzdt}=on"
        f"&subregion=&leftlon=220&rightlon=300&toplat=55&bottomlat=20"
        f"&dir=%2Fgfs.{date_str}%2F{hour_str}%2Fatmos"
    )
    response = requests.get(url_dzdt, stream=True)
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
    # GFS vertical velocity is usually 'dzdt'
    data = ds['wz'].values

    fig = plt.figure(figsize=(10, 7), dpi=600)
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([-126, -69, 24, 50], crs=ccrs.PlateCarree())

    if 'latitude' in ds and 'longitude' in ds:
        lats = ds['latitude'].values
        lons = ds['longitude'].values
        lons_plot = np.where(lons > 180, lons - 360, lons)
        if lats.ndim == 1 and lons.ndim == 1:
            Lon2d, Lat2d = np.meshgrid(lons_plot, lats)
            data2d = data.squeeze()
        else:
            Lon2d, Lat2d = lons_plot, lats
            data2d = data.squeeze()
        
        # Mask negative values to only plot positive values
        data2d = np.where(data2d > 0, data2d, np.nan)
        
        # Dynamically calculate the maximum value for the levels
        max_value = np.nanmax(data2d)
        levels = np.arange(0.1, max_value + 0.1, 0.1) if max_value > 0 else [0.1]

        # Use shaded contours for vertical velocity
        cs = ax.contourf(
            Lon2d, Lat2d, data2d,
            levels=levels,
            cmap="rainbow",  # Improved color scheme
            transform=ccrs.PlateCarree()
        )

    ax.set_axis_off()
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    png_path = os.path.join(png_dir, f"vertical_velocity_{step:03d}.png")
    plt.savefig(png_path, bbox_inches='tight', pad_inches=0, transparent=True, dpi=600)
    plt.close(fig)
    print(f"Generated clean PNG: {png_path}")
    return png_path

# Main process: Download and plot
grib_files = []
png_files = []
forecast_steps = list(range(6, 385, 6))
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
print("All GRIB file download and PNG creation tasks complete!")
