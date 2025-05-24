import subprocess
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

scripts = [
    "REFC.py",
    "mslp_script.py",
    "temp2m.py",
    "LIGHTNING.py"
]

# Each script runs sequentially; the next starts only after the previous finishes
for script in scripts:
    script_path = os.path.join(BASE_DIR, script)
    print(f"Running {script} ...")
    try:
        result = subprocess.run([sys.executable, script_path], check=True, capture_output=True, text=True)
        print(result.stdout)
        print(f"{script} completed successfully.\n")
    except subprocess.CalledProcessError as e:
        print(f"Error running {script}:\n{e.stderr}\n")
        break
