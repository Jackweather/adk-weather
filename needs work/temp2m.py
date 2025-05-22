import os
import requests
from datetime import datetime, timedelta
import xarray as xr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import cartopy.crs as ccrs  # Added import
import matplotlib.patheffects as path_effects

# --- Clean up old files in grib_files and static/2mtemp directories ---
for folder in [
    os.path.join("Hrrr", "static", "2mtemp", "grib_files"),  # New grib_files location
    os.path.join("Hrrr", "static", "2mtemp")
]:
    if os.path.exists(folder):
        for f in os.listdir(folder):
            file_path = os.path.join(folder, f)
            if os.path.isfile(file_path):
                os.remove(file_path)

# Directories
base_url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl"
output_dir = "Hrrr"
temp2m_dir = os.path.join(output_dir, "static", "2mtemp")
grib_dir = os.path.join(temp2m_dir, "grib_files")  # Now inside 2mtemp
os.makedirs(grib_dir, exist_ok=True)
os.makedirs(temp2m_dir, exist_ok=True)

# Get the current UTC date and time and subtract 6 hours
current_utc_time = datetime.utcnow() - timedelta(hours=6)
date_str = current_utc_time.strftime("%Y%m%d")
hour_str = str(current_utc_time.hour // 6 * 6).zfill(2)  # Adjust to nearest 6-hour slot

variable_tmp = "TMP"

# Custom colormap for temperature
custom_cmap = LinearSegmentedColormap.from_list(
    "custom_cmap",
    ["darkblue", "blue", "lightblue", "green", "yellow", "orange", "red"]
)

# NY_ASOS Network stations: (ID, Name, Latitude, Longitude)
NY_ASOS_STATIONS = [
     ("ISP", "Islip", 40.7952, -73.1002),                  # Long Island
    ("FOK", "Westhampton Beach", 40.8437, -72.6318),      # Long Island
    ("HPN", "White Plains", 41.0669, -73.7076),           # Just north of NYC
    ("ALB", "Albany", 42.7576, -73.8036),
    ("ART", "Watertown", 43.9888, -76.0262),
    ("BGM", "Binghamton", 42.2086, -75.9797),
    ("BUF", "Buffalo", 42.9408, -78.7358),
    ("DKK", "Dunkirk", 42.4933, -79.272),
    ("DSV", "Dansville", 42.5709, -77.713),
    ("ELM", "Elmira", 42.1571, -76.8994),
    ("GFL", "Glens Falls", 43.3412, -73.6103),
    ("ITH", "Ithaca", 42.491, -76.4584),
    ("JHW", "Jamestown", 42.1533, -79.2581),
    ("MSS", "Massena", 44.9358, -74.8456),
    ("NYC", "Central Park", 40.7794, -73.9692),           # Remove if too close to LGA/JFK
    ("OGS", "Ogdensburg", 44.6819, -75.4655),
    ("PEO", "Penn Yan", 42.6373, -77.0522),
    ("PBG", "Plattsburgh Intl", 44.6509, -73.4681),
    ("ROC", "Rochester", 43.1189, -77.6724),
    ("RME", "Rome", 43.2338, -75.4061),
    ("SLK", "Saranac Lake", 44.3853, -74.2062),
    ("SWF", "Newburgh", 41.5041, -74.1048),
    ("SYR", "Syracuse", 43.1112, -76.1063),
    
]

# Function to download GRIB files
def download_file(hour_str, step):
    file_name = f"hrrr.t{hour_str}z.wrfsfcf{step:02d}.grib2"
    file_path = os.path.join(grib_dir, file_name)  # Save to new grib_dir
    url_tmp = (f"{base_url}?dir=%2Fhrrr.{date_str}%2Fconus&file={file_name}"
               f"&var_{variable_tmp}=on&lev_2_m_above_ground=on")
    response = requests.get(url_tmp, stream=True)
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
    data = ds['t2m'].values - 273.15  # Kelvin to Celsius

    fig = plt.figure(figsize=(10, 7), dpi=600)
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([-126, -69, 24, 50], crs=ccrs.PlateCarree())

    # Get lats/lons from dataset if available, else use imshow as fallback
    if 'latitude' in ds and 'longitude' in ds:
        lats = ds['latitude'].values
        lons = ds['longitude'].values
        # Convert lons from 0-360 to -180 to 180 for plotting and matching
        lons_plot = np.where(lons > 180, lons - 360, lons)
        mesh = ax.pcolormesh(
            lons_plot, lats, data.squeeze(),
            cmap=custom_cmap,
            shading='auto',
            transform=ccrs.PlateCarree()
        )
        # Plot temperature values at NY_ASOS stations (after mesh, with high zorder)
        for stn_id, stn_name, stn_lat, stn_lon in NY_ASOS_STATIONS:
            # Convert station lon to 0-360 for matching grid
            stn_lon_grid = stn_lon if stn_lon >= 0 else stn_lon + 360
            if lats.ndim == 2 and lons.ndim == 2:
                dist = (lats - stn_lat)**2 + (lons - stn_lon_grid)**2
                iy, ix = np.unravel_index(np.argmin(dist), dist.shape)
            else:
                iy = np.abs(lats - stn_lat).argmin()
                ix = np.abs(lons - stn_lon_grid).argmin()
            temp_val = data.squeeze()[iy, ix]
            temp_f = temp_val * 9/5 + 32  # Convert Celsius to Fahrenheit
            # Plot the temperature value as white text with black outline
            txt = ax.text(
                stn_lon, stn_lat, f"{temp_f:.1f}",
                color='white', fontsize=2, fontweight='bold', fontname='DejaVu Sans',
                ha='center', va='center', transform=ccrs.PlateCarree(),
                zorder=10
            )
            txt.set_path_effects([
                path_effects.Stroke(linewidth=2, foreground='black'),
                path_effects.Normal()
            ])
    else:
        # fallback to imshow if no lat/lon
        leaflet_extent = [-125, -66.5, 24.5, 49.5]
        mesh = ax.imshow(
            data.squeeze(),
            cmap=custom_cmap,
            extent=leaflet_extent,
            origin='lower',
            interpolation='bilinear',
            aspect='auto',
            transform=ccrs.PlateCarree()
        )
        # Cannot plot station values without lat/lon grid

    ax.set_axis_off()
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    png_path = os.path.join(temp2m_dir, f"2mtemp_{step:02d}.png")
    plt.savefig(png_path, bbox_inches='tight', pad_inches=0, transparent=True, dpi=600)
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
