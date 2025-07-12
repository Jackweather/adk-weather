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
import scipy.ndimage as ndimage  # Add this import for local extrema detection

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Clean up old files in grib_files, pngs, and mslp_surface directories ---
for folder in [
    os.path.join(BASE_DIR, "GFS", "static", "gfs_mslp_surface", "grib_files"),
    os.path.join(BASE_DIR, "GFS", "static", "pngs"),
    os.path.join(BASE_DIR, "GFS", "static", "gfs_mslp_surface")
]:
    if os.path.exists(folder):
        for f in os.listdir(folder):
            file_path = os.path.join(folder, f)
            if os.path.isfile(file_path):
                os.remove(file_path)

# Directories
output_dir = os.path.join(BASE_DIR, "GFS")
mslp_surface_dir = os.path.join(output_dir, "static", "gfs_mslp_surface")
grib_dir = os.path.join(mslp_surface_dir, "grib_files")
png_dir = mslp_surface_dir
os.makedirs(grib_dir, exist_ok=True)
os.makedirs(png_dir, exist_ok=True)

# GFS 1.0° NOMADS URL and variable
base_url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_1p00.pl"
variable_mslp = "MSLET"
# Current UTC time minus 6 hours (nearest available GFS cycle)
current_utc_time = datetime.utcnow() - timedelta(hours=6)
date_str = current_utc_time.strftime("%Y%m%d")
hour_str = str(current_utc_time.hour // 6 * 6).zfill(2)  # nearest 6-hour slot

# Custom colormap and levels for MSLP (hPa)
mslp_levels = np.arange(960, 1050+4, 4)  # 960 to 1050 hPa, every 4 hPa
custom_cmap = LinearSegmentedColormap.from_list(
    "mslp_cmap",
    [
        "#08306b", "#2171b5", "#6baed6", "#b3cde3", "#ffffff",
        "#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"
    ],
    N=256
)

# NY_ASOS Network stations: (ID, Name, Latitude, Longitude)
NY_ASOS_STATIONS = [
    # ...existing station list from tmp_surface.py...
]

# Function to download GRIB files (GFS 1.0°)
def download_file(hour_str, step):
    file_name = f"gfs.t{hour_str}z.pgrb2.1p00.f{step:03d}"
    file_path = os.path.join(grib_dir, file_name)
    url_mslp = (
        f"{base_url}?file={file_name}"
        f"&lev_mean_sea_level=on&var_{variable_mslp}=on"
        f"&subregion=&leftlon=220&rightlon=300&toplat=55&bottomlat=20"
        f"&dir=%2Fgfs.{date_str}%2F{hour_str}%2Fatmos"
    )
    response = requests.get(url_mslp, stream=True)
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
    # GFS MSLP is usually 'mslet'
    data = ds['mslet'].values / 100.0  # Pa to hPa

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
        # Use contour lines instead of filled contours
        cs = ax.contour(
            Lon2d, Lat2d, data2d,
            levels=mslp_levels,
            colors='black',
            linewidths=1.5,  # Increased from 0.5 to 1.5 for thicker lines
            transform=ccrs.PlateCarree()
        )
        ax.clabel(cs, fmt='%d', fontsize=4, colors='black', inline=True)

        # --- Highs and Lows detection ---
        # Only search for extrema within the plotted region
        mask = (
            (Lon2d >= -126) & (Lon2d <= -69) &
            (Lat2d >= 24) & (Lat2d <= 50)
        )
        data_masked = np.where(mask, data2d, np.nan)

        # Find local maxima (Highs)
        max_filt = ndimage.maximum_filter(data_masked, size=25, mode='constant', cval=np.nan)
        highs = (data_masked == max_filt) & ~np.isnan(data_masked)
        high_y, high_x = np.where(highs)
        for y, x in zip(high_y, high_x):
            ax.text(
                Lon2d[y, x], Lat2d[y, x], "H",
                color='blue', fontsize=16, fontweight='bold',  # Increased fontsize from 8 to 16
                ha='center', va='center', transform=ccrs.PlateCarree(),
                zorder=3, path_effects=[path_effects.Stroke(linewidth=1, foreground='white'), path_effects.Normal()]
            )
            ax.text(
                Lon2d[y, x], Lat2d[y, x]-0.7, f"{data2d[y, x]:.0f}",
                color='blue', fontsize=5, fontweight='bold',
                ha='center', va='top', transform=ccrs.PlateCarree(),
                zorder=3, path_effects=[path_effects.Stroke(linewidth=0.5, foreground='white'), path_effects.Normal()]
            )

        # Find local minima (Lows)
        min_filt = ndimage.minimum_filter(data_masked, size=25, mode='constant', cval=np.nan)
        lows = (data_masked == min_filt) & ~np.isnan(data_masked)
        low_y, low_x = np.where(lows)
        for y, x in zip(low_y, low_x):
            ax.text(
                Lon2d[y, x], Lat2d[y, x], "L",
                color='red', fontsize=16, fontweight='bold',  # Increased fontsize from 8 to 16
                ha='center', va='center', transform=ccrs.PlateCarree(),
                zorder=3, path_effects=[path_effects.Stroke(linewidth=1, foreground='white'), path_effects.Normal()]
            )
            ax.text(
                Lon2d[y, x], Lat2d[y, x]-0.7, f"{data2d[y, x]:.0f}",
                color='red', fontsize=5, fontweight='bold',
                ha='center', va='top', transform=ccrs.PlateCarree(),
                zorder=3, path_effects=[path_effects.Stroke(linewidth=0.5, foreground='white'), path_effects.Normal()]
            )
        # --- End Highs and Lows ---

        for stn_id, stn_name, stn_lat, stn_lon in NY_ASOS_STATIONS:
            stn_lon_grid = stn_lon if stn_lon >= 0 else stn_lon + 360
            if lats.ndim == 2 and lons.ndim == 2:
                dist = (lats - stn_lat)**2 + (lons - stn_lon_grid)**2
                iy, ix = np.unravel_index(np.argmin(dist), dist.shape)
            else:
                iy = np.abs(lats - stn_lat).argmin()
                ix = np.abs(lons - stn_lon_grid).argmin()
            mslp_val = data.squeeze()[iy, ix]
            txt = ax.text(
                stn_lon, stn_lat, f"{mslp_val:.1f}",
                color='white', fontsize=1, fontweight='bold', fontname='DejaVu Sans',
                ha='center', va='center', transform=ccrs.PlateCarree(),
                zorder=2
            )
            txt.set_path_effects([
                path_effects.Stroke(linewidth=3.5, foreground='black'),
                path_effects.Normal()
            ])
    else:
        leaflet_extent = [-126, -69, 24, 50]
        # For fallback, just plot the image (not contours)
        mesh = ax.imshow(
            data.squeeze(),
            cmap=custom_cmap,
            extent=leaflet_extent,
            origin='lower',
            interpolation='bilinear',
            aspect='auto',
            transform=ccrs.PlateCarree()
        )

    ax.set_axis_off()
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    png_path = os.path.join(png_dir, f"mslp_{step:03d}.png")
    plt.savefig(png_path, bbox_inches='tight', pad_inches=0, transparent=True, dpi=600)
    plt.close(fig)
    print(f"Generated clean PNG: {png_path}")
    return png_path

# Main process: Download and plot
grib_files = []
png_files = []
forecast_steps = list(range(6, 385, 6))
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
