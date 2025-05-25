import os
import requests
from datetime import datetime, timedelta
import xarray as xr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import cartopy.crs as ccrs  # for geographic plotting

# --- Clean up old files ---
for folder in [
    os.path.join("Hrrr", "static", "MSLP", "grib_files"),
    os.path.join("Hrrr", "static", "MSLP")
]:
    if os.path.exists(folder):
        for f in os.listdir(folder):
            file_path = os.path.join(folder, f)
            if os.path.isfile(file_path):
                os.remove(file_path)

# Directories
base_url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl"
output_dir = "Hrrr"
mslp_dir = os.path.join(output_dir, "static", "MSLP")
grib_dir = os.path.join(mslp_dir, "grib_files")
os.makedirs(grib_dir, exist_ok=True)
os.makedirs(mslp_dir, exist_ok=True)

# Current UTC time minus 6 hours (nearest HRRR cycle)
current_utc_time = datetime.utcnow() - timedelta(hours=6)
date_str = current_utc_time.strftime("%Y%m%d")
hour_str = str((current_utc_time.hour // 6) * 6).zfill(2)  # nearest 6-hour slot
variable_mslma = "MSLMA"

def download_file(hour_str, step):
    file_name = f"hrrr.t{hour_str}z.wrfsfcf{step:02d}.grib2"
    file_path = os.path.join(grib_dir, file_name)
    url = (f"{base_url}?dir=%2Fhrrr.{date_str}%2Fconus&file={file_name}"
           f"&var_{variable_mslma}=on&lev_mean_sea_level=on")
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

def generate_png(file_path, step):
    try:
        ds = xr.open_dataset(file_path, engine="cfgrib")

        # Check for the variable presence (some datasets may not have MSLMA)
        if variable_mslma.lower() not in ds.variables:
            print(f"[step {step}] Skipping: '{variable_mslma.lower()}' variable not found.")
            return None

        data = ds[variable_mslma.lower()].values / 100  # Convert Pa to hPa

        # Skip empty or all NaN arrays
        if data.size == 0 or np.isnan(data).all():
            print(f"[step {step}] Skipping: data empty or all NaN.")
            return None

        # Extract lat/lon coordinates robustly
        try:
            if 'latitude' in ds.coords and 'longitude' in ds.coords:
                lats = ds.coords['latitude'].values
                lons = ds.coords['longitude'].values
            else:
                lats = ds['latitude'].values
                lons = ds['longitude'].values
        except Exception as e:
            print(f"[step {step}] Skipping: failed to extract lat/lon ({e})")
            return None

        if lats.size == 0 or lons.size == 0:
            print(f"[step {step}] Skipping: latitude or longitude array empty.")
            return None

        # Meshgrid if lats/lons are 1D
        if lats.ndim == 1 and lons.ndim == 1:
            lons, lats = np.meshgrid(lons, lats)

        # Attempt to fix shape mismatches
        if data.shape != lats.shape or data.shape != lons.shape:
            # Transpose if needed
            if lats.T.shape == data.shape and lons.T.shape == data.shape:
                lats = lats.T
                lons = lons.T
            # Squeeze dims if needed
            elif np.squeeze(lats).shape == data.shape and np.squeeze(lons).shape == data.shape:
                lats = np.squeeze(lats)
                lons = np.squeeze(lons)
            elif lats.shape == np.squeeze(data).shape and lons.shape == np.squeeze(data).shape:
                data = np.squeeze(data)
            else:
                print(f"[step {step}] Skipping: shape mismatch after attempts (data: {data.shape}, lats: {lats.shape}, lons: {lons.shape})")
                return None

        fig = plt.figure(figsize=(10, 7), dpi=850)
        ax = plt.axes(projection=ccrs.PlateCarree())
        ax.set_extent([-126, -69, 24, 50], crs=ccrs.PlateCarree())

        levels = np.arange(np.floor(np.nanmin(data)), np.ceil(np.nanmax(data)) + 1, 2)
        cs = ax.contour(
            lons, lats, data,
            levels=levels,
            cmap="coolwarm",
            linewidths=1
        )
        ax.clabel(cs, inline=True, fontsize=8, fmt='%1.0f')

        # Plot high and low pressure markers
        min_idx = np.unravel_index(np.nanargmin(data), data.shape)
        max_idx = np.unravel_index(np.nanargmax(data), data.shape)
        ax.text(lons[min_idx], lats[min_idx], 'L', color='blue', fontsize=24, fontweight='bold',
                ha='center', va='center', transform=ccrs.PlateCarree())
        ax.text(lons[max_idx], lats[max_idx], 'H', color='red', fontsize=24, fontweight='bold',
                ha='center', va='center', transform=ccrs.PlateCarree())

        ax.set_axis_off()
        plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
        png_path = os.path.join(mslp_dir, f"MSLP_{step:02d}.png")
        plt.savefig(png_path, bbox_inches='tight', pad_inches=0, transparent=True)
        plt.close(fig)
        print(f"[step {step}] PNG created: {png_path}")
        return png_path

    except Exception as e:
        print(f"[step {step}] Skipping due to error: {e}")
        return None

# Main loop: download and generate PNGs
grib_files = []
png_files = []
for step in range(0, 49):
    grib_file = download_file(hour_str, step)
    if grib_file:
        grib_files.append(grib_file)
        png_file = generate_png(grib_file, step)
        png_files.append(png_file)

print("All downloads and PNG creation complete!")
