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

# Current UTC time minus 6 hours (nearest available HRRR cycle)
current_utc_time = datetime.utcnow() - timedelta(hours=6)
date_str = current_utc_time.strftime("%Y%m%d")
hour_str = str(current_utc_time.hour // 6 * 6).zfill(2)  # nearest 6-hour slot

variable_tmp = "TMP"

# Custom colormap and levels for temperature (°F)
temp_levels = [-20, 0, 10, 20, 32, 40, 50, 60, 70, 80, 90, 100]  # For colorbar use later, in Fahrenheit
custom_cmap = LinearSegmentedColormap.from_list(
    "temp_cmap",
    [
        "#08306b",  # very cold (dark blue)
        "#2171b5",  # cold (blue)
        "#6baed6",  # chilly (light blue)
        "#ffffff",  # freezing (white, 32F)
        "#ffffb2",  # cool (light yellow)
        "#fecc5c",  # mild (yellow)
        "#fd8d3c",  # warm (orange)
        "#f03b20",  # hot (red-orange)
        "#bd0026"   # very hot (dark red)
    ],
    N=256
)

# NY_ASOS Network stations: (ID, Name, Latitude, Longitude)
NY_ASOS_STATIONS = [
    ("PGV", "Greenville", 35.6127, -77.3664),            # Greenville, NC
    ("PIT", "Pittsburgh", 40.4406, -79.9959),            # Pittsburgh, PA
    ("SHV", "Shreveport", 32.5252, -93.7502),            # Shreveport, LA
    ("DSM", "Des Moines", 41.5868, -93.6250),            # Iowa
    ("GDV", "Glendive", 47.1050, -104.7102),             # Montana
    ("CDC", "Cedar City", 37.6775, -113.0619),           # Utah
    ("MCI", "Kansas City", 39.0997, -94.5786),           # Missouri
    ("UOX", "Oxford", 34.3665, -89.5342),                # Mississippi
    ("HSV", "Huntsville", 34.7304, -86.5861),            # Alabama
    ("CSG", "Columbus", 32.4609, -84.9877),              # Georgia
    ("TLH", "Tallahassee", 30.4383, -84.2807),           # Florida
    ("WMC", "Winnemucca", 40.9729, -117.7357),           # Nevada
    ("PHX", "Phoenix", 33.4484, -112.0740),              # Arizona
    ("ABQ", "Albuquerque", 35.0844, -106.6504),          # New Mexico
    ("OKC", "Oklahoma City", 35.4676, -97.5164),         # Oklahoma
    ("LSE", "La Crosse", 43.8014, -91.2396),             # Wisconsin
    ("SLC", "Salt Lake City", 40.7608, -111.8910),       # Utah
    ("SHV", "Shreveport", 32.5252, -93.7502),            # Louisiana
    ("MSY", "New Orleans", 29.9511, -90.0715),           # Louisiana
    ("ICT", "Wichita", 37.6872, -97.3301),               # Kansas
    ("AIA", "Alliance", 42.1014, -102.8724),             # Nebraska
    ("MSN", "Madison", 43.0731, -89.4012),               # Wisconsin
    ("DLH", "Duluth", 46.7867, -92.1005),                # Minnesota
    ("DTW", "Detroit", 42.3314, -83.0458),               # Michigan
    ("TVC", "Traverse City", 44.7631, -85.6206),         # Michigan
    ("SPI", "Springfield", 39.7817, -89.6501),           # Illinois
    ("IND", "Indianapolis", 39.7684, -86.1581),          # Indiana
    ("LEX", "Lexington", 38.0406, -84.5037),             # Kentucky
    ("CGI", "Cape Girardeau", 37.3059, -89.5181),        # Missouri
    ("CRW", "Charleston", 38.3498, -81.6326),            # West Virginia
    ("ABE", "Allentown", 40.6084, -75.4902),             # Pennsylvania
    ("ACY", "Atlantic City", 39.3643, -74.4229),         # New Jersey
    ("YNG", "Youngstown", 41.0998, -80.6495),            # Ohio
    ("RUT", "Rutland", 43.6106, -72.9726),               # Vermont
    ("GFD", "Greenfield", 42.5876, -72.5995),            # Massachusetts
    ("BOS", "Boston", 42.3601, -71.0589),                # Massachusetts
    ("NPT", "Newport", 41.4901, -71.3128),               # Rhode Island
    ("WAT", "Waterbury", 41.5582, -73.0515),             # Connecticut
    ("GON", "New London", 41.3557, -72.0995),            # Connecticut
    ("CON", "Concord", 43.2081, -71.5376),               # New Hampshire
    ("AUG", "Augusta", 44.3106, -69.7795),               # Maine
    ("CPR", "Casper", 42.8666, -106.3131),               # Wyoming
    ("BOI", "Boise", 43.6150, -116.2023),                # Idaho
    ("PDX", "Portland", 45.5152, -122.6784),             # Oregon
    ("SEA", "Seattle", 47.6062, -122.3321),              # Washington
    ("RAP", "Rapid City", 44.0805, -103.2310),           # South Dakota
    ("LIT", "Little Rock", 34.7465, -92.2896),           # Arkansas
    ("MEM", "Memphis", 35.1495, -90.0490),               # Tennessee
    ("MOB", "Mobile", 30.6954, -88.0399),                # Alabama
    ("TPA", "Tampa", 27.9506, -82.4572),                 # Florida
    ("MIA", "Miami", 25.7617, -80.1918),                 # Florida
    ("JAX", "Jacksonville", 30.3322, -81.6557),          # Florida
    ("MYR", "Myrtle Beach", 33.6891, -78.8867),          # South Carolina
    ("AVL", "Asheville", 35.5951, -82.5515),             # North Carolina
    ("RIC", "Richmond", 37.5407, -77.4360),              # Virginia
    ("CMH", "Columbus", 39.9612, -82.9988),              # Ohio
    ("OMA", "Omaha", 41.2565, -95.9345),                 # Nebraska
    ("FAR", "Fargo", 46.8772, -96.7898),                 # North Dakota
    ("GTF", "Great Falls", 47.4942, -111.2833),          # Montana
    ("SJC", "San Jose", 37.3541, -121.9552),             # California
    ("LAS", "Las Vegas", 36.1699, -115.1398),            # Nevada
    ("DFW", "Dallas", 32.7767, -96.7970),                # Texas
    ("CRP", "Corpus Christi", 27.8006, -97.3964),        # Texas
    ("AMA", "Amarillo", 35.2219, -101.8313),             # Texas
    ("DENVER", "Denver", 39.7392, -104.9903),            # Colorado, not necessarily ASOS
    ("ISP", "Islip", 40.7952, -73.1002),                 # Long Island
    ("FOK", "Westhampton Beach", 40.8437, -72.6318),     # Long Island
    ("HPN", "White Plains", 41.0669, -73.7076),          # Just north of NYC
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
    # Added Andes, NY and Old Forge, NY
    ("AND", "Andes", 42.1906, -74.7857),
    ("OLF", "Old Forge", 43.7117, -74.9732),
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
                color='white', fontsize=1, fontweight='bold', fontname='DejaVu Sans',
                ha='center', va='center', transform=ccrs.PlateCarree(),
                zorder=2
            )
            txt.set_path_effects([
                path_effects.Stroke(linewidth=0.5, foreground='black'),
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
