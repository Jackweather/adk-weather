import os
import requests
from PIL import Image
import time
from io import BytesIO
import math
from datetime import datetime, timezone, timedelta
import pytz  # Add this import

# Explicitly set the directory to weatherdata/satellite
BASE_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
IMG_DIR = os.path.join(BASE_DIR, "weatherdata", "satellite")
os.makedirs(IMG_DIR, exist_ok=True)

# CONUS bounds (lat/lon)
SW_LAT, SW_LON = 24.396308, -125.0
NE_LAT, NE_LON = 49.384358, -66.93457

OUT_WIDTH = 12288   # Increased for higher detail
OUT_HEIGHT = 8192

# Tile settings
TILE_SIZE = 256
ZOOM = 6  # Use zoom 4 for reasonable detail

def latlon_to_tilexy(lat, lon, zoom):
    """Convert lat/lon to tile x/y at a given zoom (Web Mercator)"""
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    xtile = (lon + 180.0) / 360.0 * n
    ytile = (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n
    return xtile, ytile

def fetch_tile(z, x, y):
    url = f"http://mesonet.agron.iastate.edu/cache/tile.py/1.0.0/conus-goes-vis-1km/{z}/{x}/{y}.png"
    resp = requests.get(url)
    if resp.status_code == 200:
        return Image.open(BytesIO(resp.content)).convert("RGBA")
    else:
        return Image.new("RGBA", (TILE_SIZE, TILE_SIZE), (0,0,0,0))

def save_conus_snapshot():
    # Calculate tile range for bounds
    x0, y1 = latlon_to_tilexy(SW_LAT, SW_LON, ZOOM)
    x1, y0 = latlon_to_tilexy(NE_LAT, NE_LON, ZOOM)
    x0, x1 = int(math.floor(x0)), int(math.ceil(x1))
    y0, y1 = int(math.floor(y0)), int(math.ceil(y1))
    # Create a blank image to hold all tiles
    tile_cols = x1 - x0
    tile_rows = y1 - y0
    full_img = Image.new("RGBA", (tile_cols * TILE_SIZE, tile_rows * TILE_SIZE))
    # Paste tiles
    for x in range(x0, x1):
        for y in range(y0, y1):
            tile = fetch_tile(ZOOM, x, y)
            px = (x - x0) * TILE_SIZE
            py = (y - y0) * TILE_SIZE
            full_img.paste(tile, (px, py))
    # Crop to exact bounds
    # Calculate pixel offsets for SW/NE in the stitched image
    sw_xtile, sw_ytile = latlon_to_tilexy(SW_LAT, SW_LON, ZOOM)
    ne_xtile, ne_ytile = latlon_to_tilexy(NE_LAT, NE_LON, ZOOM)
    left = int((sw_xtile - x0) * TILE_SIZE)
    right = int((ne_xtile - x0) * TILE_SIZE)
    top = int((ne_ytile - y0) * TILE_SIZE)
    bottom = int((sw_ytile - y0) * TILE_SIZE)
    cropped = full_img.crop((left, top, right, bottom))
    # Resize to desired output size
    out_img = cropped.resize((OUT_WIDTH, OUT_HEIGHT), Image.LANCZOS)
    # Use YYMMDD_HHMMAM/PM_EST timestamp in filename
    now_utc = datetime.utcnow().replace(tzinfo=timezone.utc)
    eastern = pytz.timezone('US/Eastern')
    now_est = now_utc.astimezone(eastern)
    # Format: yymmdd_HHMMAM/PM_EST.png (12-hour time)
    filename = now_est.strftime("%y%m%d_%I%M%p_EST.png")
    filepath = os.path.join(IMG_DIR, filename)
    # Save with very high DPI metadata (for printing, not browser)
    out_img.save(filepath, dpi=(2400, 2400))
    print(f"Saved CONUS snapshot as {filepath} ({OUT_WIDTH}x{OUT_HEIGHT})")

def clear_pngs_near_midnight(buffer_minutes=7):
    """Delete all PNGs in IMG_DIR during a 7-minute buffer around midnight (Eastern Time)."""
    eastern = pytz.timezone('US/Eastern')
    cleared_today = False
    now = datetime.now(eastern)
    # Check if we are in the buffer period (23:53 to 00:00)
    if now.hour == 23 and now.minute >= (60 - buffer_minutes):
        # In buffer period: clear PNGs if not already cleared today
        if not cleared_today:
            for fname in os.listdir(IMG_DIR):
                if fname.lower().endswith('.png'):
                    try:
                        os.remove(os.path.join(IMG_DIR, fname))
                    except Exception as e:
                        print(f"Failed to delete {fname}: {e}")
            print(f"Cleared all PNGs in {IMG_DIR} during buffer before midnight Eastern.")
            cleared_today = True

if __name__ == "__main__":
    clear_pngs_near_midnight()
    save_conus_snapshot()
