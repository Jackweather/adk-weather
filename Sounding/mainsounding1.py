# Example: Load and plot a sounding using SHARPpy's scripting interface

import os
import requests
from bs4 import BeautifulSoup
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use Agg for headless plotting
import matplotlib.pyplot as plt
import io
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import random

def fetch_bufkit_text(url, local_file):
    # Ensure the output folder exists
    output_folder = os.path.join(os.path.dirname(__file__), "bufkit_files")
    os.makedirs(output_folder, exist_ok=True)
    local_file = os.path.join(output_folder, os.path.basename(local_file))
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

def calc_wetbulb_c(pres_hpa, temp_c, dewpoint_c):
    """
    Approximate wet-bulb temperature (°C) using Stull's formula.
    pres_hpa: pressure in hPa
    temp_c: temperature in °C
    dewpoint_c: dewpoint in °C
    Returns: wet-bulb temperature in °C (array)
    """
    # Vectorized Stull (2011) formula, valid for most surface conditions
    # https://journals.ametsoc.org/view/journals/apme/50/11/jamc-d-11-0143.1.xml
    t = temp_c
    td = dewpoint_c
    tw = t * np.arctan(0.151977 * np.sqrt(td + 8.313659)) + \
         np.arctan(t + td) - np.arctan(td - 1.676331) + \
         0.00391838 * (td ** 1.5) * np.arctan(0.023101 * td) - 4.686035
    return tw

def parse_bufkit(raw):
    """
    Parse BUFKIT text and extract all soundings (by TIME) as a list of dicts.
    Each dict contains: 'time', 'lat', 'lon', 'pres', 'tmpc', 'dwpc', 'drct', 'sknt', 'hght', 'tmwc', 'meta'
    """
    lines = raw.splitlines()
    soundings = []
    i = 0
    while i < len(lines):
        # Look for start of a sounding (TIME = ...)
        if "TIME =" in lines[i]:
            meta = {}
            # Parse meta block (TIME, SLAT, SLON, etc.)
            while i < len(lines) and lines[i].strip():
                line = lines[i]
                if "TIME" in line:
                    # Example: TIME = 250607/1800
                    time_str = line.split("TIME")[1].split("=")[1].strip()
                    meta['time'] = time_str
                if "SLAT" in line and "SLON" in line:
                    try:
                        parts = line.replace('=', ' = ').split()
                        slat_idx = parts.index('SLAT')
                        slon_idx = parts.index('SLON')
                        meta['lat'] = float(parts[slat_idx + 2])
                        meta['lon'] = float(parts[slon_idx + 2])
                    except Exception:
                        pass
                i += 1
            # Look for header line (PRES ...)
            while i < len(lines) and not (lines[i].strip().startswith("PRES") and "TMPC" in lines[i] and "DWPC" in lines[i]):
                i += 1
            if i >= len(lines):
                break
            header_idx = i
            header_cols = lines[header_idx].split()
            tmwc_idx = header_cols.index("TMWC") if "TMWC" in header_cols else None
            # Parse data lines (8+2 columns, as before)
            data = []
            i += 1
            while i < len(lines):
                # Find next non-blank line for line1
                while i < len(lines) and not lines[i].strip():
                    i += 1
                if i >= len(lines):
                    break
                line1 = lines[i].strip()
                # Stop if we hit a new TIME or header
                if "TIME =" in line1 or line1.startswith("PRES"):
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
                if len(parts1) == 8 and len(parts2) == 2:
                    try:
                        floats = [float(x) for x in parts1 + parts2]
                        data.append(floats)
                    except ValueError:
                        pass
                    i = j + 1
                else:
                    i = j
            if data:
                arr = np.array(data, dtype=float)
                pres = arr[:,0]
                tmpc = arr[:,1]
                dwpc = arr[:,3]
                drct = arr[:,5]
                sknt = arr[:,6]
                hght = arr[:,9]
                tmwc = arr[:,tmwc_idx] if tmwc_idx is not None else np.full_like(tmpc, np.nan)
                sounding = {
                    'time': meta.get('time', None),
                    'lat': meta.get('lat', None),
                    'lon': meta.get('lon', None),
                    'pres': pres,
                    'tmpc': tmpc,
                    'dwpc': dwpc,
                    'drct': drct,
                    'sknt': sknt,
                    'hght': hght,
                    'tmwc': tmwc,
                    'meta': meta
                }
                soundings.append(sounding)
        else:
            i += 1
    return soundings

def list_stations_from_url(directory_url):
    """
    Fetches all .buf files from the given directory URL, just like the other code.
    Returns a sorted list of .buf filenames.
    """
    response = requests.get(directory_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    station_files = [a['href'] for a in soup.find_all('a', href=True) if a['href'].endswith('.buf')]
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

def extract_first_time_from_bufkit(raw):
    """
    Extracts the first TIME = ... line from BUFKIT file text.
    Returns (YYYY, MM, DD, HH) as strings, or None if not found.
    """
    for line in raw.splitlines():
        if "TIME" in line and "=" in line:
            # Example: TIME = 250607/1800
            try:
                time_str = line.split("TIME")[1].split("=")[1].strip()
                # time_str: YYMMDD/HHMM
                date_part, hour_part = time_str.split("/")
                yy = int(date_part[:2])
                yyyy = 2000 + yy if yy < 70 else 1900 + yy  # crude Y2K logic
                mm = int(date_part[2:4])
                dd = int(date_part[4:6])
                hh = int(hour_part[:2])
                return f"{yyyy:04d}", f"{mm:02d}", f"{dd:02d}", f"{hh:02d}"
            except Exception:
                continue
    return None

# --- Thermodynamic functions ---

def dry_adiabat(temp_c, pres_hpa, ref_pres_hpa=1000.0):
    """
    Calculate the temperature (°C) along a dry adiabat for a given pressure.
    temp_c: starting temperature at ref_pres_hpa (°C)
    pres_hpa: pressure(s) (hPa)
    ref_pres_hpa: reference pressure (hPa), default 1000 hPa
    """
    temp_k = temp_c + 273.15
    theta = temp_k * (ref_pres_hpa / pres_hpa) ** 0.286
    return theta - 273.15

def moist_adiabat(temp_c, pres_hpa):
    """
    Approximate the moist adiabatic temperature (°C) for a parcel lifted from temp_c at 1000 hPa.
    Uses a simplified iterative approach.
    """
    # This is a simplified version for plotting reference lines
    temp = temp_c + 273.15
    p0 = 1000.0
    t_out = []
    for p in pres_hpa:
        t = temp
        for _ in range(10):
            es = 6.112 * np.exp(17.67 * (t - 273.15) / (t - 29.65))
            ws = 0.622 * es / (p - es)
            lapse = 9.8 * (1 + 0.81 * ws) / (1 + 0.61 * ws)
            t = t - lapse * np.log(p0 / p) / 10
        t_out.append(t - 273.15)
    return np.array(t_out)

def saturation_mixing_ratio(pres_hpa, temp_c):
    """
    Calculate the saturation mixing ratio (g/kg) at given pressure and temperature.
    """
    es = 6.112 * np.exp(17.67 * temp_c / (temp_c + 243.5))
    ws = 622.0 * es / (pres_hpa - es)
    return ws

def main():
    from datetime import datetime, timedelta

    # Get the current UTC date and time and select the most recent HRRR run (0z, 6z, 12z, 18z)
    current_utc_time = datetime.utcnow()
    run_hour = (current_utc_time.hour // 6) * 6
    if run_hour == 24:
        run_hour = 18
    date_for_run = current_utc_time
    if current_utc_time.hour < run_hour:
        # If current hour is less than run_hour (shouldn't happen with integer division, but safe)
        date_for_run = current_utc_time - timedelta(hours=6)
        run_hour = (date_for_run.hour // 6) * 6
    date_str = date_for_run.strftime("%Y%m%d")
    hour_str = str(run_hour).zfill(2)  # 00, 06, 12, 18

    # Compose the directory URL for the most recent HRRR run
    directory_url = f"https://mtarchive.geol.iastate.edu/{date_for_run.strftime('%Y/%m/%d')}/bufkit/{hour_str}/hrrr/"

    # --- Delete all files in bufkit_files before loading new ones ---
    output_folder = os.path.join(os.path.dirname(__file__), "bufkit_files")
    if os.path.exists(output_folder):
        for fname in os.listdir(output_folder):
            fpath = os.path.join(output_folder, fname)
            try:
                os.remove(fpath)
            except Exception:
                pass
    else:
        os.makedirs(output_folder, exist_ok=True)

    print("Fetching available stations...")

    # --- Setup figure and axes ---
    fig = plt.figure(figsize=(12,8))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([-126, -69, 24, 50], crs=ccrs.PlateCarree())
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_title("")
    ax.set_facecolor('none')
    fig.patch.set_facecolor('none')
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    # Remove all spines (axes borders)
    for spine in ax.spines.values():
        spine.set_visible(False)

    # --- State for dynamic update ---
    scat = None
    dot_to_station = {}
    station_locations = {}

    def update_stations():
        nonlocal scat, dot_to_station, station_locations
        try:
            stations = list_stations_from_url(directory_url)
            if not stations:
                print("No stations found at the URL.")
                # Clear map if no stations
                if scat is not None:
                    scat.remove()
                    scat = None
                dot_to_station = {}
                station_locations = {}
                fig.canvas.draw_idle()
                return

            # --- Remove all files in bufkit_files except marker before downloading new ones ---
            output_folder = os.path.join(os.path.dirname(__file__), "bufkit_files")
            for fname in os.listdir(output_folder):
                if fname != ".download_complete":
                    try:
                        os.remove(os.path.join(output_folder, fname))
                    except Exception:
                        pass

            # --- Prioritize and load at least 20 stations within a NY lat/lon bounding box ---
            # NY bounding box: approx lat 40.4 to 45.1, lon -79.8 to -71.8
            ny_lat_min, ny_lat_max = 40.4, 45.1
            ny_lon_min, ny_lon_max = -79.8, -71.8

            ny_stations = []
            other_stations = []
            must_have = []

            # Always include these two files, regardless of directory_url
            always_kbuf = "hrrr_kbuf.buf"
            always_kalb = "hrrr_kalb.buf"
            must_have.extend([always_kbuf, always_kalb])

            for fname in stations:
                # Skip if already in must_have
                if fname in must_have:
                    continue
                bufkit_path = os.path.join(os.path.dirname(__file__), "bufkit_files", fname)
                latlon = None
                if os.path.exists(bufkit_path):
                    try:
                        with open(bufkit_path, "r", encoding="utf-8") as f:
                            header = "\n".join([next(f) for _ in range(30)])
                        latlon = extract_latlon_from_bufkit(header)
                    except Exception:
                        pass
                if not latlon:
                    other_stations.append(fname)
                    continue
                lat, lon = latlon
                if ny_lat_min <= lat <= ny_lat_max and ny_lon_min <= lon <= ny_lon_max:
                    ny_stations.append(fname)
                else:
                    other_stations.append(fname)
            # Remove duplicates in must_have (in case KBUF/KALB are also in ny_stations)
            must_have = list(dict.fromkeys(must_have))
            # Remove must_have from ny_stations/other_stations if present
            ny_stations = [s for s in ny_stations if s not in must_have]
            other_stations = [s for s in other_stations if s not in must_have]
            random.shuffle(ny_stations)
            random.shuffle(other_stations)
            # Ensure at least 20 NY stations (including must_have), fill up to 50 with others
            ny_needed = max(0, 20 - len(must_have))
            selected_ny = must_have + ny_stations[:ny_needed]
            selected_other = other_stations[:50 - len(selected_ny)]
            stations = selected_ny + selected_other

            # Only run this logic the first time, then skip on future timer calls
            if hasattr(update_stations, "already_loaded") and update_stations.already_loaded:
                return
            update_stations.already_loaded = True

            new_station_locations = {}

            # --- Only keep the current 50 files in bufkit_files ---
            # (No need to repeat deletion here, already done above)

            # Download only missing files for the current 50
            for fname in stations:
                bufkit_url = directory_url + fname
                local_file_path = os.path.join(output_folder, fname)
                if not os.path.exists(local_file_path):
                    try:
                        response = requests.get(bufkit_url)
                        response.raise_for_status()
                        with open(local_file_path, "w", encoding="utf-8") as f:
                            f.write(response.text)
                        header = "\n".join(response.text.splitlines()[:30])
                        latlon = extract_latlon_from_bufkit(header)
                        if latlon:
                            new_station_locations[fname] = latlon
                    except Exception as e:
                        print(f"Failed to download or parse {fname}: {e}")
                        continue
                else:
                    try:
                        with open(local_file_path, "r", encoding="utf-8") as f:
                            header = "\n".join([next(f) for _ in range(30)])
                        latlon = extract_latlon_from_bufkit(header)
                        if latlon:
                            new_station_locations[fname] = latlon
                    except Exception:
                        continue

            if not new_station_locations:
                print("No stations with valid SLAT/SLON found.")
                # Clear map if no valid stations
                if scat is not None:
                    scat.remove()
                    scat = None
                dot_to_station = {}
                station_locations = {}
                fig.canvas.draw_idle()
                return

            # Update scatter plot
            lats, lons, names = [], [], []
            for fname, (lat, lon) in new_station_locations.items():
                lats.append(lat)
                lons.append(lon)
                names.append(fname)

            if scat is not None:
                scat.remove()
            scat = ax.scatter(lons, lats, c='red', s=60, marker='o', picker=True, zorder=5)
            dot_to_station = {i: names[i] for i in range(len(names))}
            station_locations = new_station_locations
            fig.canvas.draw_idle()
        except Exception as e:
            print("Error updating stations:", e)

    skewt_open = [False]  # Use a mutable object to allow modification in nested functions

    def onpick(event):
        # --- New Skew-T with arrow key navigation ---
        import matplotlib.pyplot as plt
        from metpy.plots import SkewT
        from mpl_toolkits.axes_grid1.inset_locator import inset_axes
        from metpy.plots import Hodograph
        import metpy.calc as mpcalc
        from metpy.units import units
        import matplotlib.colors as mcolors
        import numpy as np
        import pandas as pd

        ind = event.ind[0]
        station_file = dot_to_station[ind]
        bufkit_url = directory_url + station_file
        sounding_file = os.path.basename(bufkit_url)
        print(f"Selected: {station_file}")
        raw = fetch_bufkit_text(bufkit_url, sounding_file)
        try:
            soundings = parse_bufkit(raw)
            if not soundings:
                print("No soundings found in file.")
                return

            time_idx = [0]

            def plot_skewt(idx):
                buf = soundings[idx]
                df = pd.DataFrame({
                    'pres': buf['pres'],
                    'tmpc': buf['tmpc'],
                    'dwpc': buf['dwpc'],
                    'tmwc': buf['tmwc'],
                    'drct': buf['drct'],
                    'sknt': buf['sknt'],
                    'hght': buf['hght']
                })

                # Convert to MetPy units
                P = df['pres'].values * units.hPa
                T = df['tmpc'].values * units.degC
                Td = df['dwpc'].values * units.degC
                u, v = mpcalc.wind_components(df['sknt'].values * units.knots, df['drct'].values * units.degrees)
                # For barbs, only plot every ~50 hPa
                idx_barb = [np.abs(P.m - p).argmin() for p in np.arange(1000, 99, -50) if np.any(np.abs(P.m - p) < 25)]

                # LCL and parcel profile
                pBot, pTop = 1050, 100
                tMin, tMax = -40, 50
                lclp, lclt = mpcalc.lcl(P[0], T[0], Td[0])
                parcel_prof = mpcalc.parcel_profile(P, T[0], Td[0]).to('degC')

                # Create a new figure. The dimensions here give a good aspect ratio
                fig = plt.figure(figsize=(9, 9))
                skew = SkewT(fig, rotation=45)

                # Plot the data using normal plotting functions
                skew.plot(P, T, 'r', linewidth=4)  # Bolder temperature line
                skew.plot(P, Td, color='#228B22', linewidth=4)  # Bolder, darker green dewpoint
                skew.plot_barbs(P[idx_barb], u[idx_barb], v[idx_barb])
                skew.ax.set_ylim(pBot, pTop)
                skew.ax.set_xlim(tMin, tMax)

                # Plot LCL as black dot
                skew.plot(lclp, lclt, 'ko', markerfacecolor='black')

                # Plot the parcel profile as a bold black dashed line
                skew.plot(P, parcel_prof, 'k', linestyle='--', linewidth=3)

                # Plot a zero degree isotherm
                skew.ax.axvline(0, color='c', linestyle='-', linewidth=2)

                # Add the relevant special lines
                skew.plot_dry_adiabats()
                skew.plot_moist_adiabats(colors='#58a358', linestyle='-')
                skew.plot_mixing_lines()

                # Title
                date_str = buf['time'] if buf['time'] else "Unknown Date"
                model = "HRRR"
                lat, lon = station_locations.get(station_file, (None, None))
                if lat is None or lon is None:
                    lat, lon = buf.get('lat', None), buf.get('lon', None)
                latlon_str = f"{lat:.2f}°N, {lon:.2f}°W" if lat is not None and lon is not None else "Lat/Lon: N/A"
                plt.title(f"HRRR Sounding {latlon_str} Init: {date_str} | Model: {model}", fontsize=15, pad=15, color="#22223b")

                # Hodograph inset (smaller, with colorbar for height)
                ax_hod = inset_axes(skew.ax, '28%', '28%', loc=1, borderpad=2)
                h = Hodograph(ax_hod, component_range=100.)
                ax_hod.set_facecolor('white')
                # Draw faint circles every 20 knots
                for r in range(20, 101, 20):
                    circ = plt.Circle((0, 0), r, color="#adb5bd", fill=False, linewidth=0.7, alpha=0.4, zorder=0)
                    ax_hod.add_patch(circ)
                # Draw grid lines and set ticks/labels for -15 to 50
                ax_hod.set_xticks(np.arange(-15, 51, 5))
                ax_hod.set_yticks(np.arange(-15, 51, 5))
                ax_hod.set_xlim(-15, 50)
                ax_hod.set_ylim(-15, 50)
                ax_hod.grid(True, color="#dee2e6", linestyle="--", linewidth=0.7, alpha=0.7, zorder=0)
                # Axis labels
                ax_hod.set_xlabel("U (kt)", fontsize=9)
                ax_hod.set_ylabel("V (kt)", fontsize=9)
                # Tick label style
                ax_hod.tick_params(axis='both', which='major', labelsize=8, colors="#495057")
                # Draw crosshairs
                ax_hod.axhline(0, color="#adb5bd", lw=0.8, alpha=0.8, zorder=0)
                ax_hod.axvline(0, color="#adb5bd", lw=0.8, alpha=0.8, zorder=0)
                # Custom colormap: low=red→green, mid=purple, high=blue
                hght = df['hght'].values
                hmin, hmax = np.nanmin(hght), np.nanmax(hght)
                norm = mcolors.Normalize(vmin=hmin, vmax=hmax)
                custom_cmap = mcolors.LinearSegmentedColormap.from_list(
                    "custom_hodo", [
                        (0.0, "#ff2d00"),   # bright red (low)
                        (0.3, "#00ff00"),   # green (low-mid)
                        (0.6, "#a259e6"),   # purple (mid-high)
                        (1.0, "#0096ff"),   # blue (very high)
                    ]
                )
                lc = h.plot_colormapped(u, v, hght, cmap=custom_cmap, norm=norm, linewidth=2.5)

                plt.tight_layout(rect=[0.07, 0.04, 0.98, 0.97])

                # Print all available times for this station, highlight current
                print("\nAvailable times for this station:")
                for i, s in enumerate(soundings):
                    prefix = "-> " if i == idx else "   "
                    print(f"{prefix}{i}: {s['time']}")

                def on_skewt_key(event):
                    if event.key in ["right", "ArrowRight"]:
                        if time_idx[0] < len(soundings) - 1:
                            time_idx[0] += 1
                            plt.close(fig)
                            plot_skewt(time_idx[0])
                    elif event.key in ["left", "ArrowLeft"]:
                        if time_idx[0] > 0:
                            time_idx[0] -= 1
                            plt.close(fig)
                            plot_skewt(time_idx[0])
                fig.canvas.mpl_connect('key_press_event', on_skewt_key)

                plt.show()

            plot_skewt(time_idx[0])
        except Exception as e:
            print("Error parsing BUFKIT data:", e)
        skewt_open[0] = False  # Mark Skew-T as closed after plot window closes

    fig.canvas.mpl_connect('pick_event', onpick)

    # --- Initial station plot ---
    update_stations()

    # --- Periodic update using matplotlib timer (every 60 seconds) ---
    timer = fig.canvas.new_timer(interval=60000)
    timer.add_callback(update_stations)
    timer.start()

    # --- Write marker file to signal downloads are complete ---
    output_folder = os.path.join(os.path.dirname(__file__), "bufkit_files")
    marker_path = os.path.join(output_folder, ".download_complete")
    with open(marker_path, "w") as f:
        f.write("done")

    plt.show()

# REMOVE or COMMENT OUT this function to avoid confusion with static Flask PNG endpoint
def plot_skewt_from_bufkit(bufkit_path, time_idx=0):
    # Read the bufkit file
    with open(bufkit_path, "r", encoding="utf-8") as f:
        raw = f.read()
    soundings = parse_bufkit(raw)
    if not soundings:
        raise Exception("No soundings found in file.")
    if time_idx < 0 or time_idx >= len(soundings):
        raise Exception("Invalid time index.")
    buf = soundings[time_idx]
    import pandas as pd
    import numpy as np
    from metpy.plots import SkewT
    import metpy.calc as mpcalc
    from metpy.units import units
    from mpl_toolkits.axes_grid1.inset_locator import inset_axes
    from metpy.plots import Hodograph
    import matplotlib.colors as mcolors

    df = pd.DataFrame({
        'pres': buf['pres'],
        'tmpc': buf['tmpc'],
        'dwpc': buf['dwpc'],
        'tmwc': buf['tmwc'],
        'drct': buf['drct'],
        'sknt': buf['sknt'],
        'hght': buf['hght']
    })

    # Convert to MetPy units
    P = df['pres'].values * units.hPa
    T = df['tmpc'].values * units.degC
    Td = df['dwpc'].values * units.degC
    u, v = mpcalc.wind_components(df['sknt'].values * units.knots, df['drct'].values * units.degrees)
    idx_barb = [np.abs(P.m - p).argmin() for p in np.arange(1000, 99, -50) if np.any(np.abs(P.m - p) < 25)]

    lclp, lclt = mpcalc.lcl(P[0], T[0], Td[0])
    parcel_prof = mpcalc.parcel_profile(P, T[0], Td[0]).to('degC')

    # --- Skew-T style matching your interactive plot ---
    fig = plt.figure(figsize=(9, 9))
    skew = SkewT(fig, rotation=45)
    skew.plot(P, T, 'r', linewidth=4)
    skew.plot(P, Td, color='#228B22', linewidth=4)
    skew.plot_barbs(P[idx_barb], u[idx_barb], v[idx_barb])
    skew.ax.set_ylim(1050, 100)
    skew.ax.set_xlim(-40, 50)
    skew.plot(lclp, lclt, 'ko', markerfacecolor='black')
    skew.plot(P, parcel_prof, 'k', linestyle='--', linewidth=3)
    skew.ax.axvline(0, color='c', linestyle='-', linewidth=2)
    skew.plot_dry_adiabats()
    skew.plot_moist_adiabats(colors='#58a358', linestyle='-')
    skew.plot_mixing_lines()

    # Title with lat/lon if available
    lat = buf.get('lat', None)
    lon = buf.get('lon', None)
    latlon_str = f"{lat:.2f}°N, {lon:.2f}°W" if lat is not None and lon is not None else "Lat/Lon: N/A"
    plt.title(f"HRRR Sounding {latlon_str} Init: {buf.get('time','')} | Model: HRRR", fontsize=15, pad=15, color="#22223b")

    # Hodograph inset (optional, but matches your style)
    ax_hod = inset_axes(skew.ax, '28%', '28%', loc=1, borderpad=2)
    h = Hodograph(ax_hod, component_range=100.)
    ax_hod.set_facecolor('white')
    # Draw faint circles every 20 knots
    for r in range(20, 101, 20):
        circ = plt.Circle((0, 0), r, color="#adb5bd", fill=False, linewidth=0.7, alpha=0.4, zorder=0)
        ax_hod.add_patch(circ)
    # Draw grid lines and set ticks/labels for -15 to 50
    ax_hod.set_xticks(np.arange(-15, 51, 5))
    ax_hod.set_yticks(np.arange(-15, 51, 5))
    ax_hod.set_xlim(-15, 50)
    ax_hod.set_ylim(-15, 50)
    ax_hod.grid(True, color="#dee2e6", linestyle="--", linewidth=0.7, alpha=0.7, zorder=0)
    # Axis labels
    ax_hod.set_xlabel("U (kt)", fontsize=9)
    ax_hod.set_ylabel("V (kt)", fontsize=9)
    ax_hod.tick_params(axis='both', which='major', labelsize=8, colors="#495057")
    # Draw crosshairs
    ax_hod.axhline(0, color="#adb5bd", lw=0.8, alpha=0.8, zorder=0)
    ax_hod.axvline(0, color="#adb5bd", lw=0.8, alpha=0.8, zorder=0)
    # Custom colormap: low=red→green, mid=purple, high=blue
    hght = df['hght'].values
    hmin, hmax = np.nanmin(hght), np.nanmax(hght)
    norm = mcolors.Normalize(vmin=hmin, vmax=hmax)
    custom_cmap = mcolors.LinearSegmentedColormap.from_list(
        "custom_hodo", [
            (0.0, "#ff2d00"),
            (0.3, "#00ff00"),
            (0.6, "#a259e6"),
            (1.0, "#0096ff"),
        ]
    )
    lc = h.plot_colormapped(u, v, hght, cmap=custom_cmap, norm=norm, linewidth=2.5)

    plt.tight_layout(rect=[0.07, 0.04, 0.98, 0.97])

    buf_io = io.BytesIO()
    plt.savefig(buf_io, format="png", bbox_inches="tight", dpi=120)
    plt.close(fig)
    buf_io.seek(0)
    return buf_io.read()

if __name__ == "__main__":
    main()
