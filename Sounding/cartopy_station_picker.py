# Example: Load and plot a sounding using SHARPpy's scripting interface

import os
import requests
from bs4 import BeautifulSoup
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import cartopy.crs as ccrs
import cartopy.feature as cfeature
matplotlib.use('TkAgg')  # Add this line at the top after imports

def fetch_bufkit_text(url, local_file):
    if not os.path.exists(local_file):
        print(f"Webscraping {url} ...")
        response = requests.get(url)
        response.raise_for_status()
        # If the file is served as plain text, just save it
        content_type = response.headers.get('Content-Type', '')
        if 'text' in content_type or 'plain' in content_type:
            text = response.text
        else:
            # Try to extract text from HTML using BeautifulSoup
            soup = BeautifulSoup(response.content, "html.parser")
            text = soup.get_text()
        with open(local_file, "w", encoding="utf-8") as f:
            f.write(text)
        print("Download complete.")
    with open(local_file, "r", encoding="utf-8") as f:
        return f.read()

def parse_bufkit(raw):
    """
    Parse BUFKIT text and extract the first sounding arrays for SHARPpy.
    Handles split-line BUFKIT format (8 columns + 2 columns), skipping blank lines.
    Returns: dict with keys: 'pres', 'tmpc', 'dwpc', 'drct', 'sknt', 'hght'
    """
    lines = raw.splitlines()
    data_start = None
    for i, line in enumerate(lines):
        if line.strip().startswith("PRES") and "TMPC" in line and "DWPC" in line:
            data_start = i + 1
            break
    if data_start is None:
        raise ValueError("Could not find data header in BUFKIT file.")

    data = []
    i = data_start
    print("DEBUG: Scanning for data lines after header at line", data_start)
    while i < len(lines):
        # Find next non-blank line for line1
        while i < len(lines) and not lines[i].strip():
            i += 1
        if i >= len(lines):
            break
        line1 = lines[i].strip()
        # Stop if we hit a new header (e.g., STID = ...) or a new data header
        if line1.startswith("STID") or line1.startswith("PRES"):
            print(f"DEBUG: Stopping at line {i}: {line1}")
            break
        # Find next non-blank line for line2
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        if j >= len(lines):
            break
        line2 = lines[j].strip()
        parts1 = line1.split()
        parts2 = line2.split()
        # Expecting 8 + 2 columns
        if len(parts1) == 8 and len(parts2) == 2:
            try:
                floats = [float(x) for x in parts1 + parts2]
                data.append(floats)
            except ValueError:
                print(f"DEBUG: Skipping lines {i}-{j} (non-numeric): {line1} | {line2}")
            i = j + 1
        else:
            print(f"DEBUG: Skipping lines {i}-{j} (unexpected column count): {line1} | {line2}")
            i = j

    print(f"DEBUG: Found {len(data)} data lines.")
    if not data:
        raise ValueError("No valid data lines found in BUFKIT file.")

    arr = np.array(data, dtype=float)
    pres = arr[:,0]
    tmpc = arr[:,1]
    dwpc = arr[:,3]
    drct = arr[:,5]
    sknt = arr[:,6]
    hght = arr[:,9]
    return {
        'pres': pres,
        'tmpc': tmpc,
        'dwpc': dwpc,
        'drct': drct,
        'sknt': sknt,
        'hght': hght
    }

def list_stations_from_url(directory_url):
    response = requests.get(directory_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    # Find all links ending with .buf
    station_files = [a['href'] for a in soup.find_all('a', href=True) if a['href'].endswith('.buf')]
    # Remove duplicates and sort
    station_files = sorted(set(station_files))
    return station_files

def c_to_f(c):
    return c * 9.0 / 5.0 + 32.0

def extract_latlon_from_bufkit(raw):
    """
    Extracts SLAT and SLON from BUFKIT file text.
    Returns (lat, lon) as floats, or None if not found.
    """
    for line in raw.splitlines():
        if "SLAT" in line and "SLON" in line:
            try:
                parts = line.replace('=', ' = ').split()
                slat_idx = parts.index('SLAT')
                slon_idx = parts.index('SLON')
                lat = float(parts[slat_idx + 2])
                lon = float(parts[slon_idx + 2])
                return lat, lon
            except Exception:
                continue
    return None

def main():
    directory_url = "https://mtarchive.geol.iastate.edu/2025/06/07/bufkit/16/hrrr/"
    print("Fetching available stations...")
    stations = list_stations_from_url(directory_url)
    if not stations:
        print("No stations found at the URL.")
        return

    # Only process the first 10 stations
    stations = stations[:10]

    # Dynamically build station locations by downloading each .buf file header
    print("Extracting station locations (may take a moment)...")
    station_locations = {}
    for fname in stations:
        bufkit_url = directory_url + fname
        local_file = os.path.basename(fname)
        try:
            # Only fetch header (first 30 lines) for efficiency
            if not os.path.exists(local_file):
                response = requests.get(bufkit_url)
                response.raise_for_status()
                lines = response.text.splitlines()[:30]
                header = "\n".join(lines)
                with open(local_file, "w", encoding="utf-8") as f:
                    f.write(response.text)
            else:
                with open(local_file, "r", encoding="utf-8") as f:
                    lines = [next(f) for _ in range(30)]
                    header = "".join(lines)
            latlon = extract_latlon_from_bufkit(header)
            if latlon:
                station_locations[fname] = latlon
        except Exception:
            continue

    if not station_locations:
        print("No stations with valid SLAT/SLON found.")
        return

    # Prepare map
    fig = plt.figure(figsize=(12,8))
    ax = plt.axes(projection=ccrs.LambertConformal())
    ax.set_extent([-125, -66.5, 24, 50], crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.STATES, linewidth=0.5)
    ax.add_feature(cfeature.BORDERS, linewidth=0.5)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
    ax.set_title("Click anywhere to view Skew-T for nearest station")

    # Prepare station locations
    lats, lons, names = [], [], []
    for fname, (lat, lon) in station_locations.items():
        lats.append(lat)
        lons.append(lon)
        names.append(fname)

    def on_click(event):
        if not event.inaxes:
            return
        # Convert click to lat/lon
        try:
            lon, lat = ax.transData.inverted().transform((event.x, event.y))
        except Exception:
            # fallback for Cartopy: use ax.projection
            xy = np.array([[event.x, event.y]])
            lonlat = ax.transData.inverted().transform(xy)[0]
            lon, lat = lonlat[0], lonlat[1]
        # Find closest station
        dists = [(np.hypot(lat - st_lat, lon - st_lon), i) for i, (st_lat, st_lon) in enumerate(zip(lats, lons))]
        min_dist, min_idx = min(dists)
        station_file = names[min_idx]
        bufkit_url = directory_url + station_file
        sounding_file = os.path.basename(bufkit_url)
        print(f"Selected nearest: {station_file}")
        raw = fetch_bufkit_text(bufkit_url, sounding_file)
        try:
            buf = parse_bufkit(raw)
            buf['tmpf'] = c_to_f(buf['tmpc'])
            buf['dwpf'] = c_to_f(buf['dwpc'])
            df = pd.DataFrame({
                'pres': buf['pres'],
                'tmpf': buf['tmpf'],
                'dwpf': buf['dwpf'],
                'drct': buf['drct'],
                'sknt': buf['sknt'],
                'hght': buf['hght']
            })
            # Plot Skew-T in a new figure
            fig_skewt, ax_skewt = plt.subplots(figsize=(9,9))
            ax_skewt.plot(df['tmpf'], df['pres'], 'r', label='Temperature (F)')
            ax_skewt.plot(df['dwpf'], df['pres'], 'g', label='Dewpoint (F)')
            ax_skewt.invert_yaxis()
            ax_skewt.set_yscale('log')
            ax_skewt.set_ylim(1050, 100)
            ax_skewt.set_xlim(-80, 110)
            ax_skewt.set_xlabel("Temperature (°F)")
            ax_skewt.set_ylabel("Pressure (hPa)")
            ax_skewt.grid(True, which='both', axis='both', linestyle='--', alpha=0.5)
            ax_skewt.legend()
            ax_skewt.set_title(f"Skew-T for {station_file} (°F)")
            plt.show()
        except Exception as e:
            print("Error parsing BUFKIT data:", e)
            print("Raw lines near data header:")
            lines = raw.splitlines()
            for idx, line in enumerate(lines):
                if line.strip().startswith("PRES") and "TMPC" in line and "DWPC" in line:
                    for l in lines[idx:idx+30]:
                        print(l)
                    break

    fig.canvas.mpl_connect('button_press_event', on_click)
    plt.show()

if __name__ == "__main__":
    main()
