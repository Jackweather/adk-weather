try:
    import pyart
except ImportError:
    print("pyart module is not installed.")
try:
    import fsspec
except ImportError:
    print("fsspec module is not installed.")
try:
    from metpy.plots import USCOUNTIES, ctables
except ImportError:
    print("metpy module is not installed.")
try:
    import matplotlib.pyplot as plt
except ImportError:
    print("matplotlib module is not installed.")
try:
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
except ImportError:
    print("cartopy module is not installed.")
import warnings
from datetime import datetime as dt
from datetime import timedelta
try:
    from scipy.ndimage import median_filter  # Import median filter
except ImportError:
    print("scipy module is not installed.")
try:
    import numpy as np  # Add import for numpy
except ImportError:
    print("numpy module is not installed.")
import os
import gc
import time

import matplotlib
matplotlib.rcParams['animation.html'] = 'html5'
from matplotlib.animation import ArtistAnimation

warnings.filterwarnings("ignore")

# Use the current time
datTime = dt.utcnow()  # Use UTC time for consistency with radar data
year = dt.strftime(datTime, format="%Y")
month = dt.strftime(datTime, format="%m")
day = dt.strftime(datTime, format="%d")
hour = dt.strftime(datTime, format="%H")
timeStr = f'{year}{month}{day}{hour}'

fs = fsspec.filesystem("s3", anon=True)

# List of radar stations
stations = ['KENX', 'KBGM', 'KTYX', 'KCXX', 'KBUF', 'KOKX']

# Creating color tables for reflectivity (every 5 dBZ starting with 5 dBZ):
ref_norm, ref_cmap = ctables.registry.get_with_steps('NWSReflectivity', 5, 5)

# Define the resolution for the map
res = '10m'

# Output directory for PNGs
output_dir = "./RADAR/avg"
os.makedirs(output_dir, exist_ok=True)  # Ensure the avg folder exists

# Clear all PNG files in the output directory before running
for fname in os.listdir(output_dir):
    if fname.endswith(".png"):
        try:
            os.remove(os.path.join(output_dir, fname))
        except Exception as e:
            print(f"Could not remove {fname}: {e}")

# Loop through each station and plot its data
for site in stations:
    # Update file patterns for the current station
    pattern = f's3://noaa-nexrad-level2/{year}/{month}/{day}/{site}/{site}{year}{month}{day}_*'
    files = sorted(fs.glob(pattern), reverse=True)  # Sort files in reverse order (newest first)

    if len(files) == 0:
        print(f"No files found for station {site}. Skipping...")
        continue

    # Select the most recent file
    latest_file = files[0]
    print(f"Processing station {site}: {latest_file}")

    # Read radar data
    radar = pyart.io.read_nexrad_archive(f's3://{latest_file}')

    # Apply a finer median filter to smooth reflectivity data
    reflectivity_data = radar.fields['reflectivity']['data']
    reflectivity_data = np.ma.masked_less(reflectivity_data, 5)  # Mask values below 5 dBZ to retain more noise
    smoothed_reflectivity = median_filter(reflectivity_data.filled(0), size=5)  # Apply median filter with a 5x5 kernel
    smoothed_reflectivity = np.ma.masked_where(reflectivity_data.mask, smoothed_reflectivity)  # Reapply mask
    radar.fields['reflectivity']['data'] = smoothed_reflectivity  # Replace with smoothed data

    # Create a new figure for each site
    fig = plt.figure(figsize=[15, 10])
    ax = plt.subplot(111, projection=ccrs.PlateCarree())
    ax.set_extent([-80, -70, 40, 45])  # Adjust as needed for the region

    # Add a high-resolution basemap (e.g., Natural Earth features)
    ax.add_feature(cfeature.LAND.with_scale('10m'), facecolor='lightgray')
    ax.add_feature(cfeature.OCEAN.with_scale('10m'), facecolor='lightblue')
    ax.add_feature(cfeature.BORDERS.with_scale('10m'), linewidth=1.0)
    ax.add_feature(cfeature.COASTLINE.with_scale('10m'), linewidth=1.0)
    ax.add_feature(cfeature.STATES.with_scale('10m'), linewidth=0.8, edgecolor='black')
    ax.add_feature(USCOUNTIES.with_scale('20m'), linewidth=0.3, edgecolor='gray')

    # Plot radar data with transparency and adjusted reflectivity range
    display = pyart.graph.RadarMapDisplay(radar)
    display.plot_ppi_map(
        field='reflectivity',
        sweep=0,
        vmin=15,
        vmax=75,
        ax=ax,
        raster=False,
        title='',
        colorbar_flag=False,
        norm=ref_norm,
        cmap=ref_cmap,
        resolution=res,
        alpha=0.8,
    )

    # Add a colorbar for this plot
    cbar = plt.colorbar(
        plt.cm.ScalarMappable(norm=ref_norm, cmap=ref_cmap),
        ax=ax,
        orientation='horizontal',
        pad=0.05,
        aspect=50,
    )
    cbar.set_label('Equivalent Reflectivity ($Z_{e}$) (dBZ)')

    # Set a title for this radar site
    plt.title(
        f"NEXRAD Reflectivity {site} {timeStr} UTC",
        fontsize=18,
        fontweight='bold',
        color='darkblue',
    )

    # Save the plot as a PNG file with higher DPI for better quality
    output_file = f"{output_dir}/NEXRAD_Reflectivity_{site}_{timeStr}.png"
    plt.savefig(output_file, dpi=1000, bbox_inches='tight', facecolor='white')
    print(f"Plot saved as {output_file}")
    plt.close(fig)
    gc.collect()
    time.sleep(2)
