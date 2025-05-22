import os
import requests
from datetime import datetime, timedelta
import xarray as xr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from matplotlib.colors import Normalize, PowerNorm
import numpy as np

# --- Clean old files ---
for folder in [
    os.path.join("Hrrr", "static", "lighting", "grib_files"),
    os.path.join("Hrrr", "static", "lighting")
]:
    if os.path.exists(folder):
        for f in os.listdir(folder):
            file_path = os.path.join(folder, f)
            if os.path.isfile(file_path):
                os.remove(file_path)

# Directories
output_dir = os.path.join("Hrrr", "static", "lighting")
grib_dir = os.path.join(output_dir, "grib_files")
os.makedirs(grib_dir, exist_ok=True)
os.makedirs(output_dir, exist_ok=True)

base_url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl"

# Get the current UTC date and time and select the most recent HRRR run (0z, 6z, 12z, 18z)
current_utc_time = datetime.utcnow()
run_hour = (current_utc_time.hour // 6) * 6
if run_hour == 24:
    run_hour = 18
date_for_run = current_utc_time
if current_utc_time.hour < run_hour:
    # If current hour is less than run_hour (shouldn't happen with integer division, but safe)
    date_for_run = current_utc_time - timedelta(hours=6)
    run_hour = (date_for_run.hour // 6) * 6
date_str = date_for_run.strftime("%Y%m%d")
hour_str = str(run_hour).zfill(2)  # 00, 06, 12, 18
variable_ltng = "LTNG"

def download_file(hour_str, step):
    file_name = f"hrrr.t{hour_str}z.wrfsfcf{step:02d}.grib2"
    file_path = os.path.join(grib_dir, file_name)
    url_ltng = (
        f"{base_url}?dir=%2Fhrrr.{date_str}%2Fconus&file={file_name}"
        f"&var_{variable_ltng}=on&lev_entire_atmosphere=on"
    )
    response = requests.get(url_ltng, stream=True)
    if response.status_code == 200:
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        return file_path
    else:
        print(f"Failed to download {file_name} (Status Code: {response.status_code})")
        return None

def count_and_plot_flashes(file_path, step):
    try:
        ds = xr.open_dataset(file_path, engine="cfgrib")

        # Find lightning variable name
        for var in ds.data_vars:
            if var.lower().startswith("ltng") or "lightning" in var.lower():
                lightning_var = var
                break
        else:
            raise ValueError("Lightning variable not found in GRIB file.")

        data = ds[lightning_var].squeeze().values  # flash counts/rates per grid cell

        # Mask zeros so they are fully transparent in the plot
        masked_data = np.ma.masked_where(data == 0, data)

        # Sum total flashes over all grid points 
        total_flashes = np.nansum(data)

        # Coordinates
        lats = ds['latitude'].values
        lons = ds['longitude'].values

        # Plot setup - ONLY plot data, no background, no coastlines, no colorbar
        plt.figure(figsize=(14, 12), dpi=200)
        ax = plt.axes(projection=ccrs.Mercator())
        ax.set_extent([-126, -69, 24, 50], crs=ccrs.PlateCarree())

        max_val = np.nanmax(data)
        if max_val == 0:
            max_val = 1  # avoid zero max in normalization

        # Use perceptually uniform colormap and PowerNorm for better contrast
        lightning_contour = ax.contourf(
            lons, lats, masked_data,
            levels=np.linspace(0, max_val, 100),  # more levels for smoothness
            cmap='inferno',  # or 'viridis', 'magma', etc.
            norm=PowerNorm(gamma=0.5, vmin=0, vmax=max_val),  # gamma < 1 boosts low values
            transform=ccrs.PlateCarree()
        )

        # Remove axis lines and labels
        plt.axis('off')

        # Remove any other map features like coastlines or borders (do NOT add them)

        plt.tight_layout()

        # Save PNG with transparent background, no padding or borders
        png_path = os.path.join(output_dir, f"lght_{step:02d}.png")
        plt.savefig(png_path, bbox_inches='tight', pad_inches=0, transparent=True)
        plt.close()

        print(f"Step {step:02d}: Total flashes = {total_flashes:.0f}, saved plot to {png_path}")
        return total_flashes

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return None

# Main
total_flashes_all_steps = 0

for step in range(0, 49):
    grib_file = download_file(hour_str, step)
    if grib_file:
        flashes = count_and_plot_flashes(grib_file, step)
        if flashes is not None:
            total_flashes_all_steps += flashes

print(f"\nTotal lightning flashes in all forecast steps combined: {total_flashes_all_steps:.0f}")
