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
try:
    import numpy as np
except ImportError:
    print("numpy module is not installed.")
import os
import gc
import time

import matplotlib
matplotlib.rcParams['animation.html'] = 'html5'

warnings.filterwarnings("ignore")

# Use the current time
datTime = dt.utcnow()
year = dt.strftime(datTime, format="%Y")
month = dt.strftime(datTime, format="%m")
day = dt.strftime(datTime, format="%d")
hour = dt.strftime(datTime, format="%H")
timeStr = f'{year}{month}{day}{hour}'

fs = fsspec.filesystem("s3", anon=True)

stations = ['KENX', 'KBGM', 'KTYX', 'KCXX', 'KBUF', 'KOKX']

# Output directory for PNGs
output_dir = os.path.join(os.path.dirname(__file__), "..", "refcraw")
output_dir = os.path.abspath(output_dir)
os.makedirs(output_dir, exist_ok=True)  # Ensure the Radar\refcraw folder exists

# Clear all PNG files in the output directory before running
for fname in os.listdir(output_dir):
    if fname.endswith(".png"):
        try:
            os.remove(os.path.join(output_dir, fname))
        except Exception as e:
            print(f"Could not remove {fname}: {e}")

for site in stations:
    fig = plt.figure(figsize=[18, 12], dpi=200)  # Increased size and DPI
    ax = plt.subplot(111, projection=ccrs.PlateCarree())
    ax.set_extent([-80, -70, 40, 45])

    ax.add_feature(cfeature.LAND.with_scale('10m'), facecolor='lightgray')
    ax.add_feature(cfeature.OCEAN.with_scale('10m'), facecolor='lightblue')
    ax.add_feature(cfeature.BORDERS.with_scale('10m'), linewidth=1.0)
    ax.add_feature(cfeature.COASTLINE.with_scale('10m'), linewidth=1.0)
    ax.add_feature(cfeature.STATES.with_scale('10m'), linewidth=0.8, edgecolor='black')
    ax.add_feature(USCOUNTIES.with_scale('20m'), linewidth=0.3, edgecolor='gray')

    ref_norm, ref_cmap = ctables.registry.get_with_steps('NWSReflectivity', 5, 5)
    res = '10m'

    pattern = f's3://noaa-nexrad-level2/{year}/{month}/{day}/{site}/{site}{year}{month}{day}_*'
    files = sorted(fs.glob(pattern), reverse=True)

    if len(files) == 0:
        print(f"No files found for station {site}. Skipping...")
        plt.close(fig)
        gc.collect()
        time.sleep(2)
        continue

    latest_file = files[0]
    print(f"Processing station {site}: {latest_file}")

    # Open the file from S3 using fsspec and pass the file object to Py-ART
    with fs.open(latest_file, 'rb') as f:
        radar = pyart.io.read_nexrad_archive(f)

    # Do NOT mask reflectivity data by range; show full 360° sweep
    # refl = radar.fields['reflectivity']['data'].copy()
    # ...no range masking...

    display = pyart.graph.RadarMapDisplay(radar)
    display.plot_ppi_map(
        field='reflectivity',
        sweep=0,
        vmin=15,
        vmax=75,
        ax=ax,
        raster=True,  # Set raster=True for higher-res pixel rendering
        title='',
        colorbar_flag=False,
        norm=ref_norm,
        cmap=ref_cmap,
        resolution=res,
        alpha=0.8,
    )

    cbar = plt.colorbar(
        plt.cm.ScalarMappable(norm=ref_norm, cmap=ref_cmap),
        ax=ax,
        orientation='horizontal',
        pad=0.05,
        aspect=50,
    )
    cbar.set_label('Equivalent Reflectivity ($Z_{e}$) (dBZ)')

    plt.title(
        f"NEXRAD Reflectivity (Raw) {site} {timeStr} UTC",
        fontsize=18,
        fontweight='bold',
        color='darkblue',
    )

    output_file = os.path.join(output_dir, f"NEXRAD_Reflectivity_Raw_{site}_{timeStr}.png")
    plt.savefig(output_file, dpi=200, bbox_inches='tight', facecolor='white')  # Already high DPI
    print(f"Plot saved as {output_file}")
    plt.close(fig)
    gc.collect()
    time.sleep(2)

