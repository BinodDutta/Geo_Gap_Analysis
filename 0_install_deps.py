import subprocess
import sys
import os

def install_requirements():
    print(">>> DIGITAL GAP ANALYSIS PROJECT SETUP <<<")
    
    # Check if requirements.txt exists
    if not os.path.exists("requirements.txt"):
        print("Error: 'requirements.txt' not found in this folder.")
        print("Please create it first.")
        return

    print("... Installing dependencies from requirements.txt ...")
    print("... This may take a minute ...\n")

    try:
        # Use subprocess to run the pip install command
        # sys.executable ensures we use the SAME python version you are currently running
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        
        print("\n>>> SUCCESS! All libraries are installed.")
        print(">>> You can now run your analysis scripts.")
        
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Installation failed. Error code: {e}")

if __name__ == "__main__":
    install_requirements()