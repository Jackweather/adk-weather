import os
import requests
from datetime import datetime, timedelta, timezone
import xarray as xr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import cartopy.crs as ccrs  # Added import

# --- Clean up old files in grib_files and static/MSLP directories ---
for folder in [os.path.join("Hrrr", "static", "MSLP", "grib_files"), os.path.join("Hrrr", "static", "MSLP")]:
    if os.path.exists(folder):
        for f in os.listdir(folder):
            file_path = os.path.join(folder, f)
            if os.path.isfile(file_path):
                os.remove(file_path)

# Directories
base_url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl"
output_dir = "Hrrr"
mslp_dir = os.path.join(output_dir, "static", "MSLP")
grib_dir = os.path.join(mslp_dir, "grib_files")  # Now inside MSLP
os.makedirs(grib_dir, exist_ok=True)
os.makedirs(mslp_dir, exist_ok=True)

# Current UTC time minus 6 hours (nearest available HRRR cycle)
current_utc_time = datetime.utcnow() - timedelta(hours=6)
date_str = current_utc_time.strftime("%Y%m%d")
hour_str = str(current_utc_time.hour // 6 * 6).zfill(2)  # nearest 6-hour slot
variable_mslma = "MSLMA"

# Function to download GRIB files (structure and time logic matches test.py)
def download_file(hour_str, step):
    file_name = f"hrrr.t{hour_str}z.wrfsfcf{step:02d}.grib2"
    file_path = os.path.join(grib_dir, file_name)
    url_mslp = (f"{base_url}?dir=%2Fhrrr.{date_str}%2Fconus&file={file_name}"
                f"&var_{variable_mslma}=on&lev_mean_sea_level=on")
    response = requests.get(url_mslp, stream=True)
    if response.status_code == 200:
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        file_size = os.path.getsize(file_path)
        print(f"Downloaded {file_name} ({file_size} bytes)")
        return file_path
    else:
        print(f"Failed to download {file_name} (Status Code: {response.status_code})")
        return None

def generate_png(file_path, step):
    ds = xr.open_dataset(file_path, engine="cfgrib")
    # Check if required variables exist
    required_vars = ['mslma', 'latitude', 'longitude']
    for var in required_vars:
        if var not in ds.variables:
            print(f"Variable '{var}' not found in {file_path}, skipping PNG generation.")
            print(f"Available variables: {list(ds.variables.keys())}")
            return None

    data = ds['mslma'].values / 100  # Convert pressure to hPa
    lats = ds['latitude'].values
    lons = ds['longitude'].values

    # Check for empty arrays or all-NaN or constant arrays
    if (
        data.size == 0 or lats.size == 0 or lons.size == 0 or
        np.all(np.isnan(data)) or
        np.nanmin(data) == np.nanmax(data)
    ):
        print(f"Invalid or empty data in {file_path}, skipping PNG generation.")
        print(f"Shapes - data: {data.shape}, lats: {lats.shape}, lons: {lons.shape}")
        print(f"data min: {np.nanmin(data) if data.size else 'n/a'}, max: {np.nanmax(data) if data.size else 'n/a'}")
        return None

    try:
        fig = plt.figure(figsize=(10, 7), dpi=850)
        ax = plt.axes(projection=ccrs.PlateCarree())  # Use PlateCarree projection
        ax.set_extent([-126, -69, 24, 50], crs=ccrs.PlateCarree())  # Set requested extent

        # Use coolwarm colormap for contour lines
        levels = np.arange(np.floor(np.nanmin(data)), np.ceil(np.nanmax(data)) + 1, 2)
        cs = ax.contour(
            lons, lats, data.squeeze(),
            levels=levels,
            cmap="coolwarm",
            linewidths=1 # Increased thickness from 1 to 2
        )
        ax.clabel(cs, inline=True, fontsize=8, fmt='%1.0f')

        # Add H and L symbols for highs and lows
        min_idx = np.unravel_index(np.nanargmin(data), data.shape)
        max_idx = np.unravel_index(np.nanargmax(data), data.shape)
        ax.text(lons[min_idx], lats[min_idx], 'L', color='blue', fontsize=24, fontweight='bold', ha='center', va='center', transform=ccrs.PlateCarree())
        ax.text(lons[max_idx], lats[max_idx], 'H', color='red', fontsize=24, fontweight='bold', ha='center', va='center', transform=ccrs.PlateCarree())

        ax.set_axis_off()
        plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
        png_path = os.path.join(mslp_dir, f"MSLP_{step:02d}.png")
        plt.savefig(png_path, bbox_inches='tight', pad_inches=0, transparent=True)
        plt.close(fig)
        print(f"Generated PNG: {png_path}")
        return png_path
    except Exception as e:
        print(f"Error generating PNG for {file_path}: {e}")
        return None

# Main process: Download and plot
grib_files = []
png_files = []
for step in range(0, 49):
    grib_file = download_file(hour_str, step)
    if grib_file:
        grib_files.append(grib_file)
        png_file = generate_png(grib_file, step)
        if png_file:  # Only append if PNG was generated
            png_files.append(png_file)

print("All download and PNG creation tasks complete!")
