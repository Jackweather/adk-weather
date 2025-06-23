import os
import shutil
from datetime import datetime, timedelta

# Calculate target datetime (UTC - 6 hours, nearest 6-hour slot)
current_utc_time = datetime.utcnow() - timedelta(hours=6)
date_str = current_utc_time.strftime("%y%m%d")
hour_str = str((current_utc_time.hour // 6) * 6).zfill(2)
folder_name = f"{date_str}_{hour_str}z"

# Define source and destination paths
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_folder = os.path.join(base_dir, "HRRRUN", "Hrrr")
dst_folder = os.path.join(base_dir, "HRRRSAVED", folder_name)

# Copy the folder and its contents
if os.path.exists(src_folder):
    shutil.copytree(src_folder, dst_folder)
    print(f"Copied {src_folder} to {dst_folder}")
else:
    print(f"Source folder does not exist: {src_folder}")