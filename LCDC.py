import os
import requests
from datetime import datetime, timedelta
import xarray as xr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize
import cartopy.crs as ccrs
import time  # Added for sleep
import gc    # Added for garbage collection

# --- Clean up old files in grib_files and pngs directories ---
for folder in [
    os.path.join("Hrrr", "static", "LCDC", "grib_files"),
    os.path.join("Hrrr", "static", "pngs"),
    os.path.join("Hrrr", "static", "LCDC")
]:
    if os.path.exists(folder):
        for f in os.listdir(folder):
            file_path = os.path.join(folder, f)
            if os.path.isfile(file_path):
                os.remove(file_path)

# Directories
base_url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl"
output_dir = "Hrrr"
lcdc_dir = os.path.join(output_dir, "static", "LCDC")
grib_dir = os.path.join(lcdc_dir, "grib_files")
os.makedirs(grib_dir, exist_ok=True)
os.makedirs(lcdc_dir, exist_ok=True)

# Get the current UTC date and time and select the most recent HRRR run (0z, 6z, 12z, 18z)
current_utc_time = datetime.utcnow()
run_hour = (current_utc_time.hour // 6) * 6
if run_hour == 24:
    run_hour = 18
date_for_run = current_utc_time
if current_utc_time.hour < run_hour:
    date_for_run = current_utc_time - timedelta(hours=6)
    run_hour = (date_for_run.hour // 6) * 6
date_str = date_for_run.strftime("%Y%m%d")
hour_str = str(run_hour).zfill(2)  # 00, 06, 12, 18



# LCDC variable and colormap
variable_lcdc = "LCDC"
def custom_lcdc_colormap():
    return LinearSegmentedColormap.from_list(
        "LCDC_BlueToWhite",
        [
            (0.0, "#00008b"),
            (0.5, "#4169e1"),
            (0.75, "#87ceeb"),
            (1.0, "#ffffff"),
        ],
        N=256
    )
cmap = custom_lcdc_colormap()
norm = Normalize(vmin=0, vmax=100)

# Function to download GRIB files
def download_file(hour_str, step):
    file_name = f"hrrr.t{hour_str}z.wrfsfcf{step:02d}.grib2"
    file_path = os.path.join(grib_dir, file_name)
    url_lcdc = (f"{base_url}?dir=%2Fhrrr.{date_str}%2Fconus&file={file_name}"
                f"&var_{variable_lcdc}=on&lev_low_cloud_layer=on")
    response = requests.get(url_lcdc, stream=True)
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

# Function to generate a clean PNG from GRIB file (with Cartopy projection)
def generate_clean_png(file_path, step):
    ds = xr.open_dataset(file_path, engine="cfgrib")
    # Use 'lcc' as the variable name for Low Cloud Cover
    lcc = ds['lcc'].where((ds['lcc'] >= 0) & (ds['lcc'] <= 100))
    lats = ds['latitude']
    lons = ds['longitude']
    fig = plt.figure(figsize=(10, 7), dpi=850)
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([-126, -69, 24, 50], crs=ccrs.PlateCarree())
    # Create an alpha mask: 0 where lcc==0, 1 elsewhere
    alpha_mask = (lcc.squeeze() != 0).astype(float)
    mesh = ax.pcolormesh(
        lons, lats, lcc.squeeze(),
        cmap=cmap, norm=norm, transform=ccrs.PlateCarree(), shading='auto', alpha=alpha_mask
    )
    ax.set_axis_off()
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    png_path = os.path.join(lcdc_dir, f"LCDC_{step:02d}.png")
    plt.savefig(png_path, bbox_inches='tight', pad_inches=0, transparent=True)
    plt.close(fig)
    print(f"Generated clean PNG: {png_path}")
    return png_path

# Main process: Download and plot
grib_files = []
png_files = []
for step in range(0, 49):  # Loop through forecast steps (00 to 48 hours)
    grib_file = download_file(hour_str, step)
    if grib_file:
        grib_files.append(grib_file)
        png_file = generate_clean_png(grib_file, step)
        png_files.append(png_file)
        gc.collect()         # Collect garbage after each PNG creation
        time.sleep(3)        # Wait 3 seconds between each step

print("All GRIB file download and PNG creation tasks complete!")
