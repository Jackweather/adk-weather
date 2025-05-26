import xarray as xr

# Path to GRIB2 file
file_path = r"C:\Users\jacfo\Downloads\weathermodelpage\Hrrr\static\MSLP\grib_files\hrrr.t18z.wrfsfcf00.grib2"

# Load GRIB2 data
ds = xr.open_dataset(file_path, engine='cfgrib')

# Print dataset info
print(ds)

# Access Mean Sea Level Pressure (check the variable names if needed)
if 'msl' in ds:
    mslp = ds['msl'] / 100  # Convert from Pa to hPa
    print(mslp)
else:
    print("MSLP (msl) variable not found. Available variables:")
    print(ds.data_vars)
print("data shape:", data.shape)
print("lons shape:", lons.shape)
print("lats shape:", lats.shape)
print("data min/max:", np.nanmin(data), np.nanmax(data))
print("levels:", levels)
