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

# --- Clean up old files in grib_files, pngs, and REFCHLCY directories ---
for folder in [
    os.path.join(BASE_DIR, "GFS", "static", "REFCHLCY", "grib_files"),
    os.path.join(BASE_DIR, "GFS", "static", "pngs"),
    os.path.join(BASE_DIR, "GFS", "static", "REFCHLCY")
]:
    if os.path.exists(folder):
        for f in os.listdir(folder):
            file_path = os.path.join(folder, f)
            if os.path.isfile(file_path):
                os.remove(file_path)

# Directories
output_dir = os.path.join(BASE_DIR, "GFS")
hlcy_dir = os.path.join(output_dir, "static", "REFCHLCY")
grib_dir = os.path.join(hlcy_dir, "grib_files")
png_dir = hlcy_dir
os.makedirs(grib_dir, exist_ok=True)
os.makedirs(png_dir, exist_ok=True)

# GFS 0.25-degree URL and variable
base_url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"
variable_hlcy = "HLCY"
level_hlcy = "3000-0_m_above_ground"
# Current UTC time minus 6 hours (nearest available GFS cycle)
current_utc_time = datetime.utcnow() - timedelta(hours=6)
date_str = current_utc_time.strftime("%Y%m%d")
hour_str = str(current_utc_time.hour // 6 * 6).zfill(2)  # nearest 6-hour slot

# Custom colormap and levels for helicity (m^2/s^2)
hlcy_levels = [50, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800]
hlcy_colors = [
    "#00ff00",  # 50: green
    "#33cc00",  # 100: dark green
    "#ffff00",  # 150: yellow
    "#ffcc00",  # 200: gold
    "#ff9900",  # 250: orange
    "#ff0000",  # 300: red
    "#cc0000",  # 400: dark red
    "#990099",  # 500: purple
    "#c800ff",  # 600: magenta
    "#ff00ff",  # 700: pink
    "#ffffff",  # 800: white
]
hlcy_cmap = LinearSegmentedColormap.from_list("hlcy_custom", hlcy_colors, N=len(hlcy_colors))

# Function to download GRIB files (GFS HLCY)
def download_file(hour_str, step):
    if step == 0:
        file_name = f"gfs.t{hour_str}z.pgrb2.0p25.f000"
    else:
        file_name = f"gfs.t{hour_str}z.pgrb2.0p25.f{step:03d}"
    file_path = os.path.join(grib_dir, file_name)
    url_hlcy = (
        f"{base_url}?file={file_name}"
        f"&lev_{level_hlcy}=on&var_{variable_hlcy}=on"
        f"&subregion=&leftlon=220&rightlon=300&toplat=55&bottomlat=20"
        f"&dir=%2Fgfs.{date_str}%2F{hour_str}%2Fatmos"
    )
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

# Function to generate a clean PNG from GRIB file (no map features)
def generate_clean_png(file_path, step):
    ds = xr.open_dataset(file_path, engine="cfgrib")
    # GFS helicity is usually 'hlcy'
    data = ds['hlcy'].values  # m^2/s^2

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
        # Filter levels to include only 250 and above
        filtered_levels = [level for level in hlcy_levels if level >= 250]
        filtered_colors = hlcy_colors[hlcy_levels.index(250):]
        contours = ax.contour(
            Lon2d, Lat2d, data2d,
            levels=filtered_levels,
            colors=filtered_colors,
            linewidths=0.5,
            transform=ccrs.PlateCarree()
        )
        ax.clabel(contours, inline=True, fontsize=6, fmt='%d')
    else:
        print("Latitude and longitude data missing in GRIB file.")
        return None

    # Remove axes
    ax.set_axis_off()
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    png_path = os.path.join(png_dir, f"hlcy_{step:03d}.png")
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
        grib_files.append(grib_file)
        png_file = generate_clean_png(grib_file, step)
        png_files.append(png_file)
        gc.collect()
        time.sleep(3)
