import subprocess
import os
import traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def run_script(script_name):
    try:
        subprocess.run(["python", os.path.join(BASE_DIR, script_name)], check=True)
        print(f"{script_name} ran successfully!")
    except subprocess.CalledProcessError:
        error_trace = traceback.format_exc()
        print(f"Error running {script_name}:\n{error_trace}")

if __name__ == "__main__":
    run_script("REFC.py")
    run_script("mslp_script.py")
    run_script("temp2m.py")
    run_script("LIGHTNING.py")
    run_script("RH.py")
    run_script("HAIL.py")
    run_script("cape.py")
    run_script("CIN.py")
    run_script("HCDC.py")
    run_script("HRRRRUNS/MCDC.py")
    run_script("HCDC.py")
    run_script("total_precip.py")
    
