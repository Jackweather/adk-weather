import xarray as xr

# Replace with the path to one of your downloaded HRRR GRIB2 files
grib_file = r'Hrrr\static\2mtemp\grib_files\hrrr.t06z.wrfsfcf01.grib2'

ds = xr.open_dataset(grib_file, engine="cfgrib")

if 'latitude' in ds and 'longitude' in ds:
    lats = ds['latitude'].values
    lons = ds['longitude'].values
    print("Latitude shape:", lats.shape)
    print("Longitude shape:", lons.shape)
    print("Latitude range: min =", lats.min(), "max =", lats.max())
    print("Longitude range: min =", lons.min(), "max =", lons.max())
    print("Sample latitudes:", lats.ravel()[:5])
    print("Sample longitudes:", lons.ravel()[:5])
else:
    print("No 'latitude' or 'longitude' variable found in the dataset.")
    print("Available variables:", list(ds.variables))
