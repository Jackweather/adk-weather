import os
import requests
from datetime import datetime, timedelta
import xarray as xr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
import cartopy.crs as ccrs  # Added for map projection

# --- Clean up old files in grib_files and pngs directories ---
for folder in [
    os.path.join("Hrrr", "static", "REFC", "grib_files"),
    os.path.join("Hrrr", "static", "pngs"),
    os.path.join("Hrrr", "static", "REFC")  # Added to clean up PNGs in REFC
]:
    if os.path.exists(folder):
        for f in os.listdir(folder):
            file_path = os.path.join(folder, f)
            if os.path.isfile(file_path):
                os.remove(file_path)
# Directories
base_url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl"
output_dir = "Hrrr"
refc_dir = os.path.join(output_dir, "static", "REFC")
grib_dir = os.path.join(refc_dir, "grib_files")  # Now inside REFC
os.makedirs(grib_dir, exist_ok=True)
os.makedirs(refc_dir, exist_ok=True)

# Get the current UTC date and time and subtract 6 hours
current_utc_time = datetime.utcnow() - timedelta(hours=6)
date_str = current_utc_time.strftime("%Y%m%d")
hour_str = str(current_utc_time.hour // 6 * 6).zfill(2)  # Adjust to nearest 6-hour slot

# Reflectivity variable and colormap
variable_refc = "REFC"
colors = [
    "#C0F2FF", "#04e9e7", "#019ff4", "#0300f4", "#02fd02",
    "#01c501", "#008e00", "#fdf802", "#e5bc00", "#fd9500",
    "#fd0000", "#d40000", "#bc0000", "#f800fd", "#9854c6", "#fdfdfd"
]
bounds = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75]
cmap = ListedColormap(colors)
norm = BoundaryNorm(bounds, cmap.N)

# Function to download GRIB files
def download_file(hour_str, step):
    file_name = f"hrrr.t{hour_str}z.wrfsfcf{step:02d}.grib2"
    file_path = os.path.join(grib_dir, file_name)
    url_refc = (f"{base_url}?dir=%2Fhrrr.{date_str}%2Fconus&file={file_name}"
                f"&var_{variable_refc}=on&lev_entire_atmosphere=on")
    response = requests.get(url_refc, stream=True)
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
    refc = ds['refc'].where((ds['refc'] >= 0) & (ds['refc'] <= 75))
    lats = ds['latitude']
    lons = ds['longitude']
    fig = plt.figure(figsize=(10, 7), dpi=850)
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([-126, -69, 24, 50], crs=ccrs.PlateCarree())
    # Use contourf for smoother, filled contours
    contour = ax.contourf(
        lons, lats, refc.squeeze(),
        levels=bounds, cmap=cmap, norm=norm, transform=ccrs.PlateCarree(), extend='max'
    )
    # Optionally, add contour lines for clarity
    # ax.contour(lons, lats, refc.squeeze(), levels=bounds, colors='k', linewidths=0.2, transform=ccrs.PlateCarree())
    ax.set_axis_off()
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    png_path = os.path.join(refc_dir, f"REFC_{step:02d}.png")
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

print("All GRIB file download and PNG creation tasks complete!")
