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
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Clean up old files in grib_files and pngs directories ---
for folder in [
    os.path.join(BASE_DIR, "Hrrr", "static", "VUCSH_VVCSH", "grib_files"),
    os.path.join(BASE_DIR, "Hrrr", "static", "VUCSH_VVCSH"),
]:
    if os.path.exists(folder):
        for f in os.listdir(folder):
            file_path = os.path.join(folder, f)
            if os.path.isfile(file_path):
                os.remove(file_path)

# Directories
base_url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl"
output_dir = os.path.join(BASE_DIR, "Hrrr")
shear_dir = os.path.join(output_dir, "static", "VUCSH_VVCSH")
grib_dir = os.path.join(shear_dir, "grib_files")
os.makedirs(grib_dir, exist_ok=True)
os.makedirs(shear_dir, exist_ok=True)

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


# Shear variables and colormaps
shear_vars = {
    "vucsh": {
        "name": "VUCSH",
        "title": "0-6 km Shear (U-component, m/s)",
        "cmap": "coolwarm",
        "bounds": [-40, -30, -20, -10, 0, 10, 20, 30, 40]
    },
    "vvcsh": {
        "name": "VVCSH",
        "title": "0-6 km Shear (V-component, m/s)",
        "cmap": "coolwarm",
        "bounds": [-40, -30, -20, -10, 0, 10, 20, 30, 40]
    }
}

# Function to download GRIB files
def download_file(hour_str, step):
    file_name = f"hrrr.t{hour_str}z.wrfsfcf{step:02d}.grib2"
    file_path = os.path.join(grib_dir, file_name)
    url = (f"{base_url}?dir=%2Fhrrr.{date_str}%2Fconus&file={file_name}"
           f"&var_VUCSH=on&var_VVCSH=on&lev_0-6000_m_above_ground=on")
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

# Function to generate PNGs for VUCSH and VVCSH
def generate_shear_pngs(file_path, step):
    ds = xr.open_dataset(file_path, engine="cfgrib")
    lats = ds['latitude']
    lons = ds['longitude']
    png_paths = []
    for var_key, var_info in shear_vars.items():
        if var_key in ds:
            data = ds[var_key].squeeze()
            fig = plt.figure(figsize=(10, 7), dpi=850)
            ax = plt.axes(projection=ccrs.PlateCarree())
            ax.set_extent([-126, -69, 24, 50], crs=ccrs.PlateCarree())
            contour = ax.contourf(
                lons, lats, data,
                levels=var_info["bounds"],
                cmap=var_info["cmap"],
                norm=BoundaryNorm(var_info["bounds"], plt.get_cmap(var_info["cmap"]).N),
                transform=ccrs.PlateCarree(), extend='both'
            )
            ax.set_axis_off()
            plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
            png_path = os.path.join(shear_dir, f"{var_info['name']}_{step:02d}.png")
            plt.savefig(png_path, bbox_inches='tight', pad_inches=0, transparent=True)
            plt.close(fig)
            print(f"Generated PNG: {png_path}")
            png_paths.append(png_path)
    return png_paths

# Function to generate wind shear vector PNGs using quiver
def generate_shear_quiver_png(file_path, step):
    ds = xr.open_dataset(file_path, engine="cfgrib")
    lats = ds['latitude']
    lons = ds['longitude']
    if 'vucsh' in ds and 'vvcsh' in ds:
        u = ds['vucsh'].squeeze()
        v = ds['vvcsh'].squeeze()
        # Average over blocks to reduce arrow density
        block = 140  # Change this value as needed for density
        lat_vals = lats.values
        lon_vals = lons.values
        u_vals = u.values
        v_vals = v.values

        # Calculate block-averaged vectors
        avg_lats, avg_lons, avg_u, avg_v = [], [], [], []
        for i in range(0, lat_vals.shape[0], block):
            for j in range(0, lon_vals.shape[1], block):
                lat_block = lat_vals[i:i+block, j:j+block]
                lon_block = lon_vals[i:i+block, j:j+block]
                u_block = u_vals[i:i+block, j:j+block]
                v_block = v_vals[i:i+block, j:j+block]
                if lat_block.size > 0 and lon_block.size > 0:
                    avg_lats.append(np.nanmean(lat_block))
                    avg_lons.append(np.nanmean(lon_block))
                    avg_u.append(np.nanmean(u_block))
                    avg_v.append(np.nanmean(v_block))

        avg_lats = np.array(avg_lats)
        avg_lons = np.array(avg_lons)
        avg_u = np.array(avg_u)
        avg_v = np.array(avg_v)

        fig = plt.figure(figsize=(10, 7), dpi=850)
        ax = plt.axes(projection=ccrs.PlateCarree())
        ax.set_extent([-126, -69, 24, 50], crs=ccrs.PlateCarree())

        # --- Color mapping for U and V arrows ---
        # Normalize for color mapping
        u_abs = np.abs(avg_u)
        v_abs = np.abs(avg_v)
        u_norm = (u_abs - u_abs.min()) / (u_abs.max() - u_abs.min() + 1e-8)
        v_norm = (v_abs - v_abs.min()) / (v_abs.max() - v_abs.min() + 1e-8)
        # Red for U, blue for V, both from light to full color
        u_colors = [(1, 0.5 + 0.5*(1-x), 0.5 + 0.5*(1-x)) for x in u_norm]  # light pink to red
        v_colors = [(0.5 + 0.5*(1-x), 0.5 + 0.5*(1-x), 1) for x in v_norm]  # light blue to blue

        # Plot U-component (red shades, horizontal arrows)
        q1 = ax.quiver(
            avg_lons, avg_lats, avg_u, np.zeros_like(avg_u),
            scale=200, width=0.003, color=u_colors, transform=ccrs.PlateCarree(), label='U-component'
        )
        # Plot V-component (blue shades, vertical arrows)
        q2 = ax.quiver(
            avg_lons, avg_lats, np.zeros_like(avg_v), avg_v,
            scale=200, width=0.003, color=v_colors, transform=ccrs.PlateCarree(), label='V-component'
        )
        # Plot Shear vector (purple, combined)
        q3 = ax.quiver(
            avg_lons, avg_lats, avg_u, avg_v,
            scale=200, width=0.003, color='purple', transform=ccrs.PlateCarree(), label='Shear vector'
        )

        png_path = os.path.join(shear_dir, f"ShearVectors_{step:02d}.png")
        plt.savefig(png_path, bbox_inches='tight', pad_inches=0, transparent=True)
        plt.close(fig)
        print(f"Generated shear vector PNG: {png_path}")
        return png_path
    return None

# Main process: Download and plot
for step in range(0, 49):
    grib_file = download_file(hour_str, step)
    if grib_file:
        generate_shear_quiver_png(grib_file, step)
        gc.collect()
        time.sleep(3)

print("All VUCSH/VVCSH GRIB file download and shear vector PNG creation tasks complete!")
