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

# --- Clean up old files in grib_files, pngs, and HAINESCY directories ---
for folder in [
    os.path.join(BASE_DIR, "GFS", "static", "HAINESCY", "grib_files"),
    os.path.join(BASE_DIR, "GFS", "static", "pngs"),
    os.path.join(BASE_DIR, "GFS", "static", "HAINESCY")
]:
    if os.path.exists(folder):
        for f in os.listdir(folder):
            file_path = os.path.join(folder, f)
            if os.path.isfile(file_path):
                os.remove(file_path)

# Directories
output_dir = os.path.join(BASE_DIR, "GFS")
haines_dir = os.path.join(output_dir, "static", "HAINESCY")
grib_dir = os.path.join(haines_dir, "grib_files")
png_dir = haines_dir
os.makedirs(grib_dir, exist_ok=True)
os.makedirs(png_dir, exist_ok=True)

# GFS 0.25-degree URL and variable
base_url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"
variable_haines = "HINDEX"
level_haines = "surface"
# Current UTC time minus 6 hours (nearest available GFS cycle)
current_utc_time = datetime.utcnow() - timedelta(hours=6)
date_str = current_utc_time.strftime("%Y%m%d")
hour_str = str(current_utc_time.hour // 6 * 6).zfill(2)  # nearest 6-hour slot

# Custom colormap and levels for Haines Index
haines_levels = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
haines_colors = [
    "#ffffff",  # 0: clear (no data)
    "#0000ff",  # 1: blue
    "#0099ff",  # 2: light blue
    "#00ff00",  # 3: green
    "#ffff00",  # 4: yellow
    "#ff9900",  # 5: orange
    "#ff6600",  # 6: orange-red
    "#ff0000",  # 7: red
    "#cc0000",  # 8: dark red
    "#990000",  # 9: very dark red
    "#660000",  # 10: darkest red
]
haines_cmap = LinearSegmentedColormap.from_list("haines_custom", haines_colors, N=len(haines_colors))

# Function to download GRIB files (GFS Haines Index)
def download_file(hour_str, step):
    if step == 0:
        file_name = f"gfs.t{hour_str}z.pgrb2.0p25.f000"
    else:
        file_name = f"gfs.t{hour_str}z.pgrb2.0p25.f{step:03d}"
    file_path = os.path.join(grib_dir, file_name)
    url_haines = (
        f"{base_url}?file={file_name}"
        f"&lev_{level_haines}=on&var_{variable_haines}=on"
        f"&subregion=&leftlon=220&rightlon=300&toplat=55&bottomlat=20"
        f"&dir=%2Fgfs.{date_str}%2F{hour_str}%2Fatmos"
    )
    response = requests.get(url_haines, stream=True)
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
    # GFS Haines Index is usually 'hindex'
    data = ds['hindex'].values

    # Make 0 values transparent
    data = np.where(data == 0, np.nan, data)

    fig = plt.figure(figsize=(10, 7), dpi=600)
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([-126, -69, 24, 50], crs=ccrs.PlateCarree())

    if 'latitude' in ds and 'longitude' in ds:
        lats = ds['latitude'].values
        lons = ds['longitude'].values
        lons_plot = np.where(lons > 180, lons - 360, lons)
        # Ensure lats, lons, and data are 2D for contour
        if lats.ndim == 1 and lons.ndim == 1:
            Lon2d, Lat2d = np.meshgrid(lons_plot, lats)
            data2d = data.squeeze()
        else:
            Lon2d, Lat2d = lons_plot, lats
            data2d = data.squeeze()
        ax.contourf(
            Lon2d, Lat2d, data2d,
            levels=haines_levels,
            cmap=haines_cmap,
            transform=ccrs.PlateCarree()
        )
    else:
        print("Latitude and longitude data missing in GRIB file.")
        return None

    # Remove axes
    ax.set_axis_off()
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    png_path = os.path.join(png_dir, f"haines_{step:03d}.png")
    plt.savefig(png_path, bbox_inches='tight', pad_inches=0, transparent=True, dpi=600)
    plt.close(fig)
    print(f"Generated clean PNG: {png_path}")
    return png_path

# Main process: Download and plot
grib_files = []
png_files = []
forecast_steps = [0] + list(range(6, 385, 6))  # include analysis step 0
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
