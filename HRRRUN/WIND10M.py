import os
import requests
from datetime import datetime, timedelta
import xarray as xr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, BoundaryNorm
import cartopy.crs as ccrs
import time
import gc
import numpy as np
import matplotlib.patheffects as patheffects

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Clean up old files in grib_files and pngs directories ---
for folder in [
    os.path.join(BASE_DIR, "Hrrr", "static", "WIND10M", "grib_files"),
    os.path.join(BASE_DIR, "Hrrr", "static", "pngs"),
    os.path.join(BASE_DIR, "Hrrr", "static", "WIND10M")
]:
    if os.path.exists(folder):
        for f in os.listdir(folder):
            file_path = os.path.join(folder, f)
            if os.path.isfile(file_path):
                os.remove(file_path)

# Directories
base_url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl"
output_dir = os.path.join(BASE_DIR, "Hrrr")
wind_dir = os.path.join(output_dir, "static", "WIND10M")
grib_dir = os.path.join(wind_dir, "grib_files")
os.makedirs(grib_dir, exist_ok=True)
os.makedirs(wind_dir, exist_ok=True)

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
hour_str = str(run_hour).zfill(2)

# Wind variable and colormap
variable_wind = "WIND"
wind_colors = [
    (0, 0, 0, 0),  # clear/transparent for 0-4 m/s
    "#c0f2ff",  # very light blue
    "#7ad6f6",  # light blue
    "#01baff",  # blue
    "#019ff4",  # deep blue
    "#90ee90",  # light green
    "#02fd02",  # green
    "#24d102",  # medium green
    "#a3fd02",  # yellow-green
    "#fdf802",  # yellow
    "#fdc502",  # yellow-orange
    "#fd9500",  # orange
    "#fd5c00",  # orange-red
    "#fd0000",  # red
    "#d40000",  # dark red
    "#bc0000",  # deeper red
    "#800080",  # purple
    "#c800c8",  # magenta
    "#ff69b4",  # pink
    "#a0522d",  # brown
    "#000000",  # black
    "#808080"   # gray
]
wind_bounds = [
    0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56, 60, 64, 68, 72, 76, 80, 84, 88, 92
]
wind_cmap = LinearSegmentedColormap.from_list("wind_speed_cmap", wind_colors, N=len(wind_bounds)-1)
norm = BoundaryNorm(wind_bounds, wind_cmap.N)

# Function to download GRIB files
def download_file(hour_str, step):
    file_name = f"hrrr.t{hour_str}z.wrfsfcf{step:02d}.grib2"
    file_path = os.path.join(grib_dir, file_name)
    url_wind = (f"{base_url}?dir=%2Fhrrr.{date_str}%2Fconus&file={file_name}"
                f"&var_{variable_wind}=on&lev_10_m_above_ground=on")
    response = requests.get(url_wind, stream=True)
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

# NY_ASOS Network stations: (ID, Name, Latitude, Longitude)
NY_ASOS_STATIONS = [
    ("PGV", "Greenville", 35.6127, -77.3664),
    ("PIT", "Pittsburgh", 40.4406, -79.9959),
    ("SHV", "Shreveport", 32.5252, -93.7502),
    ("DSM", "Des Moines", 41.5868, -93.6250),
    ("GDV", "Glendive", 47.1050, -104.7102),
    ("CDC", "Cedar City", 37.6775, -113.0619),
    ("MCI", "Kansas City", 39.0997, -94.5786),
    ("UOX", "Oxford", 34.3665, -89.5342),
    ("HSV", "Huntsville", 34.7304, -86.5861),
    ("CSG", "Columbus", 32.4609, -84.9877),
    ("TLH", "Tallahassee", 30.4383, -84.2807),
    ("WMC", "Winnemucca", 40.9729, -117.7357),
    ("PHX", "Phoenix", 33.4484, -112.0740),
    ("ABQ", "Albuquerque", 35.0844, -106.6504),
    ("OKC", "Oklahoma City", 35.4676, -97.5164),
    ("LSE", "La Crosse", 43.8014, -91.2396),
    ("SLC", "Salt Lake City", 40.7608, -111.8910),
    ("SHV", "Shreveport", 32.5252, -93.7502),
    ("MSY", "New Orleans", 29.9511, -90.0715),
    ("ICT", "Wichita", 37.6872, -97.3301),
    ("AIA", "Alliance", 42.1014, -102.8724),
    ("MSN", "Madison", 43.0731, -89.4012),
    ("DLH", "Duluth", 46.7867, -92.1005),
    ("DTW", "Detroit", 42.3314, -83.0458),
    ("TVC", "Traverse City", 44.7631, -85.6206),
    ("SPI", "Springfield", 39.7817, -89.6501),
    ("IND", "Indianapolis", 39.7684, -86.1581),
    ("LEX", "Lexington", 38.0406, -84.5037),
    ("CGI", "Cape Girardeau", 37.3059, -89.5181),
    ("CRW", "Charleston", 38.3498, -81.6326),
    ("ABE", "Allentown", 40.6084, -75.4902),
    ("ACY", "Atlantic City", 39.3643, -74.4229),
    ("YNG", "Youngstown", 41.0998, -80.6495),
    ("RUT", "Rutland", 43.6106, -72.9726),
    ("GFD", "Greenfield", 42.5876, -72.5995),
    ("BOS", "Boston", 42.3601, -71.0589),
    ("NPT", "Newport", 41.4901, -71.3128),
    ("WAT", "Waterbury", 41.5582, -73.0515),
    ("GON", "New London", 41.3557, -72.0995),
    ("CON", "Concord", 43.2081, -71.5376),
    ("AUG", "Augusta", 44.3106, -69.7795),
    ("CPR", "Casper", 42.8666, -106.3131),
    ("BOI", "Boise", 43.6150, -116.2023),
    ("PDX", "Portland", 45.5152, -122.6784),
    ("SEA", "Seattle", 47.6062, -122.3321),
    ("RAP", "Rapid City", 44.0805, -103.2310),
    ("LIT", "Little Rock", 34.7465, -92.2896),
    ("MEM", "Memphis", 35.1495, -90.0490),
    ("MOB", "Mobile", 30.6954, -88.0399),
    ("TPA", "Tampa", 27.9506, -82.4572),
    ("MIA", "Miami", 25.7617, -80.1918),
    ("JAX", "Jacksonville", 30.3322, -81.6557),
    ("MYR", "Myrtle Beach", 33.6891, -78.8867),
    ("AVL", "Asheville", 35.5951, -82.5515),
    ("RIC", "Richmond", 37.5407, -77.4360),
    ("CMH", "Columbus", 39.9612, -82.9988),
    ("OMA", "Omaha", 41.2565, -95.9345),
    ("FAR", "Fargo", 46.8772, -96.7898),
    ("GTF", "Great Falls", 47.4942, -111.2833),
    ("SJC", "San Jose", 37.3541, -121.9552),
    ("LAS", "Las Vegas", 36.1699, -115.1398),
    ("DFW", "Dallas", 32.7767, -96.7970),
    ("CRP", "Corpus Christi", 27.8006, -97.3964),
    ("AMA", "Amarillo", 35.2219, -101.8313),
    ("DENVER", "Denver", 39.7392, -104.9903),
    ("ISP", "Islip", 40.7952, -73.1002),
    ("FOK", "Westhampton Beach", 40.8437, -72.6318),
    ("HPN", "White Plains", 41.0669, -73.7076),
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
    ("NYC", "Central Park", 40.7794, -73.9692),
    ("OGS", "Ogdensburg", 44.6819, -75.4655),
    ("PEO", "Penn Yan", 42.6373, -77.0522),
    ("PBG", "Plattsburgh Intl", 44.6509, -73.4681),
    ("ROC", "Rochester", 43.1189, -77.6724),
    ("RME", "Rome", 43.2338, -75.4061),
    ("SLK", "Saranac Lake", 44.3853, -74.2062),
    ("SWF", "Newburgh", 41.5041, -74.1048),
    ("SYR", "Syracuse", 43.1112, -76.1063),
    ("AND", "Andes", 42.1906, -74.7857),
    ("OLF", "Old Forge", 43.7117, -74.9732),
]

# Function to generate a clean PNG from GRIB file (with Cartopy projection)
def generate_clean_png(file_path, step):
    ds = xr.open_dataset(file_path, engine="cfgrib")
    # Try to get the wind speed variable (HRRR may use 'wind10m' or '10u'/'10v')
    if 'wind10m' in ds:
        wind = ds['wind10m']
    elif 'max_10si' in ds:
        wind = ds['max_10si']
    elif '10u' in ds and '10v' in ds:
        wind = np.sqrt(ds['10u']**2 + ds['10v']**2)
    else:
        raise ValueError("10m wind variable not found in GRIB file")
    lats = ds['latitude']
    lons = ds['longitude']
    fig = plt.figure(figsize=(10, 7), dpi=600)  # Reduced DPI from 850 to 300
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([-126, -69, 24, 50], crs=ccrs.PlateCarree())
    contour = ax.contourf(
        lons, lats, wind.squeeze(),
        levels=wind_bounds, cmap=wind_cmap, norm=norm, transform=ccrs.PlateCarree(), extend='max'
    )
    # Plot wind values at NY_ASOS stations (after mesh, with high zorder)
    for stn_id, stn_name, stn_lat, stn_lon in NY_ASOS_STATIONS:
        # Convert station lon to 0-360 for matching grid
        stn_lon_grid = stn_lon if stn_lon >= 0 else stn_lon + 360
        try:
            if lats.ndim == 2 and lons.ndim == 2:
                lats_np = np.asarray(lats)
                lons_np = np.asarray(lons)
                dist = (lats_np - stn_lat)**2 + (lons_np - stn_lon_grid)**2
                iy, ix = np.unravel_index(np.nanargmin(dist), dist.shape)
            else:
                lats_np = np.asarray(lats)
                lons_np = np.asarray(lons)
                iy = np.abs(lats_np - stn_lat).argmin()
                ix = np.abs(lons_np - stn_lon_grid).argmin()
            wind_val = wind.squeeze()[iy, ix]
            # Plot station value over the map (after ax.set_extent)
            txt = ax.text(
                stn_lon, stn_lat, f"{wind_val:.0f}",
                color='white', fontsize=1, fontweight='bold', fontname='DejaVu Sans',
                ha='center', va='center', transform=ccrs.PlateCarree(),
                zorder=2
            )
            txt.set_path_effects([
                matplotlib.patheffects.Stroke(linewidth=0.5, foreground='black'),
                matplotlib.patheffects.Normal()
            ])
        except Exception as e:
            # Skip station if indexing fails
            continue
    else:
        # fallback to imshow if no lat/lon
        leaflet_extent = [-125, -66.5, 24.5, 49.5]
        mesh = ax.imshow(
            wind.squeeze(),
            cmap=wind_cmap,
            extent=leaflet_extent,
            origin='lower',
            interpolation='bilinear',
            aspect='auto',
            norm=norm,
            transform=ccrs.PlateCarree()
        )
        # Cannot plot station values without lat/lon grid
    ax.set_axis_off()
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    png_path = os.path.join(wind_dir, f"WIND10M_{step:02d}.png")
    plt.savefig(png_path, bbox_inches='tight', pad_inches=0, transparent=True)
    plt.close(fig)
    ds.close()  # Explicitly close xarray dataset
    del ds, wind, lats, lons, fig, ax, contour  # Free memory
    gc.collect()
    print(f"Generated clean PNG: {png_path}")
    return png_path

# Main process: Download and plot
# Remove grib_files and png_files lists to avoid holding references
for step in range(0, 49):  # Loop through forecast steps (00 to 48 hours)
    grib_file = download_file(hour_str, step)
    if grib_file:
        generate_clean_png(grib_file, step)
        os.remove(grib_file)  # Delete GRIB file after processing to save disk/memory
        gc.collect()
        time.sleep(3)

print("All GRIB file download and PNG creation tasks complete!")
