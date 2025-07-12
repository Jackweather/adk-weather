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

# --- Clean up old files in grib_files, pngs, and abs_vort directories ---
for folder in [
    os.path.join(BASE_DIR, "GFS", "static", "abs_vort", "grib_files"),
    os.path.join(BASE_DIR, "GFS", "static", "pngs"),
    os.path.join(BASE_DIR, "GFS", "static", "abs_vort")
]:
    if os.path.exists(folder):
        for f in os.listdir(folder):
            file_path = os.path.join(folder, f)
            if os.path.isfile(file_path):
                os.remove(file_path)

# Directories
output_dir = os.path.join(BASE_DIR, "GFS")
abs_vort_dir = os.path.join(output_dir, "static", "abs_vort")
grib_dir = os.path.join(abs_vort_dir, "grib_files")
png_dir = abs_vort_dir  # Save PNGs directly in abs_vort_dir
os.makedirs(grib_dir, exist_ok=True)
os.makedirs(png_dir, exist_ok=True)

# GFS 0.25° NOMADS URL and variable
base_url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"
variable_abs = "ABSV"
level = "500_mb"
# Current UTC time minus 6 hours (nearest available GFS cycle)
current_utc_time = datetime.utcnow() - timedelta(hours=6)
date_str = current_utc_time.strftime("%Y%m%d")
hour_str = str(current_utc_time.hour // 6 * 6).zfill(2)  # nearest 6-hour slot

# Custom colormap and levels for absolute vorticity (1e-5 s^-1)
abs_levels = np.arange(16, 60, 4)  # Only higher, more meteorologically significant values
custom_cmap = LinearSegmentedColormap.from_list(
    "abs_cmap",
    [
        "#ffe066",  # light orange-yellow
        "#ffb347",  # light orange
        "#ff8000",  # orange
        "#ff3300",  # red-orange
        "#cc0000",  # red
        "#660000"   # dark red
    ],
    N=256
)

# NY_ASOS Network stations: (ID, Name, Latitude, Longitude)
NY_ASOS_STATIONS = [
    # ...existing station list from tmp_surface.py...
    # (copy the full list here for consistency)
    ("PGV", "Greenville", 35.6127, -77.3664),
    ("PIT", "Pittsburgh", 40.4406, -79.9959),
    # ... (rest of the stations, unchanged) ...
    ("SCR", "Scranton", 41.4089, -75.6624),
]

# Function to download GRIB files (GFS 0.25° ABSV 500mb + HGT 500mb)
def download_file(hour_str, step):
    file_name = f"gfs.t{hour_str}z.pgrb2.0p25.f{step:03d}"
    file_path = os.path.join(grib_dir, file_name)
    url_abs = (
        f"https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"
        f"?dir=%2Fgfs.{date_str}%2F{hour_str}%2Fatmos"
        f"&file={file_name}"
        f"&var_ABSV=on"
        f"&var_HGT=on"
        f"&lev_500_mb=on"
        f"&subregion=&leftlon=220&rightlon=300&toplat=55&bottomlat=20"
    )
    response = requests.get(url_abs, stream=True)
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
    # GFS 500mb absolute vorticity is usually 'absv'
    data = ds['absv'].values * 1e5  # Convert to 1e-5 s^-1

    # Get 500mb height (HGT/gh)
    hgt_data = ds['gh'].values if 'gh' in ds else None

    fig = plt.figure(figsize=(10, 7), dpi=600)
    ax = plt.axes(projection=ccrs.PlateCarree())
    # Set the plotting extent for all map features and data
    ax.set_extent([-126, -69, 24, 50], crs=ccrs.PlateCarree())

    if 'latitude' in ds and 'longitude' in ds:
        lats = ds['latitude'].values
        lons = ds['longitude'].values
        lons_plot = np.where(lons > 180, lons - 360, lons)
        # Ensure lats, lons, and data are 2D for contourf
        if lats.ndim == 1 and lons.ndim == 1:
            Lon2d, Lat2d = np.meshgrid(lons_plot, lats)
            data2d = data.squeeze()
            hgt2d = hgt_data.squeeze() if hgt_data is not None else None
        else:
            Lon2d, Lat2d = lons_plot, lats
            data2d = data.squeeze()
            hgt2d = hgt_data.squeeze() if hgt_data is not None else None
        # Vorticity shaded (plotted over the specified extent)
        mesh = ax.contourf(
            Lon2d, Lat2d, data2d,
            levels=abs_levels,
            cmap=custom_cmap,
            extend='max',
            transform=ccrs.PlateCarree()
        )
        # 500mb height contours (thick white lines, no fill)
        if hgt2d is not None:
            # Remove NaNs for contouring
            if np.ma.is_masked(hgt2d):
                hgt2d = np.ma.filled(hgt2d, np.nan)
            hgt_levels = np.arange(4800, 6000, 60)  # typical 500mb heights in gpm
            cs = ax.contour(
                Lon2d, Lat2d, hgt2d,
                levels=hgt_levels,
                colors='Black',
                linewidths=1.4,
                linestyles='solid',
                transform=ccrs.PlateCarree()
            )
            ax.clabel(cs, fmt='%d', fontsize=6, colors='black')
        # Station labels with vorticity values
        for stn_id, stn_name, stn_lat, stn_lon in NY_ASOS_STATIONS:
            stn_lon_grid = stn_lon if stn_lon >= 0 else stn_lon + 360
            if lats.ndim == 2 and lons.ndim == 2:
                dist = (lats - stn_lat)**2 + (lons - stn_lon_grid)**2
                iy, ix = np.unravel_index(np.argmin(dist), dist.shape)
            else:
                iy = np.abs(lats - stn_lat).argmin()
                ix = np.abs(lons - stn_lon_grid).argmin()
            vort_val = data.squeeze()[iy, ix]
            txt = ax.text(
                stn_lon, stn_lat, f"{vort_val:.1f}",
                color='white', fontsize=1, fontweight='bold', fontname='DejaVu Sans',
                ha='center', va='center', transform=ccrs.PlateCarree(),
                zorder=2
            )
            txt.set_path_effects([
                path_effects.Stroke(linewidth=0.5, foreground='black'),
                path_effects.Normal()
            ])
    else:
        leaflet_extent = [-126, -69, 24, 50]
        # Fallback: imshow, also clipped to the specified extent
        mesh = ax.imshow(
            data.squeeze(),
            cmap=custom_cmap,
            extent=leaflet_extent,
            origin='lower',
            interpolation='bilinear',
            aspect='auto',
            transform=ccrs.PlateCarree()
        )
        # 500mb height contours not supported for imshow fallback

    ax.set_axis_off()
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    png_path = os.path.join(png_dir, f"absv_500mb_{step:03d}.png")
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
        gc.collect()
        time.sleep(3)

