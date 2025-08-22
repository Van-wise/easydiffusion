"""
This script checks and installs the required modules.
MODIFIED FOR MODERN ENVIRONMENTS (like Google Colab with Python 3.12)
This script is now self-contained and handles all dependencies correctly.
"""

import os
import sys
import platform
import shutil
from pathlib import Path
from pprint import pprint
from importlib.metadata import version as pkg_version, PackageNotFoundError

# --- Helper Functions ---
def version(module_name: str) -> str:
    try:
        return pkg_version(module_name)
    except PackageNotFoundError:
        return None

# --- Main Installation Logic ---
def update_modules():
    """
    Installs all necessary dependencies using modern, compatible versions
    that do not require compilation on Colab.
    """
    print("Installing all necessary dependencies for a modern environment...")

    # A comprehensive list of packages with versions known to be compatible and available on PyPI.
    packages = [
        "torchruntime",
        "sdkit==2.0.22.9", # Use the latest available 2.0.22.x version
        "stable-diffusion-sdkit==2.1.5",
        "diffusers>=0.28.0",
        "transformers>=0.28.0",
        "safetensors>=0.4.0",
        "accelerate>=0.29.0",
        "fastapi", # Let pip choose the latest compatible version
        "uvicorn[standard]", # Let pip choose the latest, [standard] includes useful extras
        "python-multipart",
        "pycloudflared",
        "rich",
        "ruamel.yaml"
    ]
    
    # We install PyTorch/Torchvision separately for GPU compatibility in Colab.
    print("Installing PyTorch for CUDA...")
    os.system(f'"{sys.executable}" -m pip install --upgrade "torch" "torchvision" --index-url https://download.pytorch.org/whl/cu121')

    # Install the rest of the packages in one go.
    print("Installing application dependencies...")
    os.system(f'"{sys.executable}" -m pip install --upgrade {" ".join(f\'"{p}"\' for p in packages)}')

    print("\n--- Final Package Versions ---")
    for module_name in ["torch", "torchvision", "sdkit", "diffusers", "transformers", "safetensors"]:
        print(f"{module_name}: {version(module_name)}")
    print("----------------------------\n")

# --- Launcher Logic (Corrected for Colab) ---
def get_config():
    config_directory = Path(__file__).parent
    config_yaml = config_directory.parent / "config.yaml"
    config = {}
    if config_yaml.is_file():
        try:
            from ruamel.yaml import YAML
            yaml = YAML(typ="safe")
            with open(config_yaml, "r", encoding="utf-8") as configfile:
                config = yaml.load(configfile)
        except Exception as e:
            print(f"Error loading config file: {e}", file=sys.stderr)
    return config if config is not None else {}

def launch_uvicorn():
    # Import torchruntime here, after it's guaranteed to be installed.
    import torchruntime

    config = get_config()
    pprint(config)

    with open("scripts/install_status.txt", "a") as f:
        f.write("sd_install_complete\n")

    print("\n\nEasy Diffusion installation complete, starting the server!\n\n")

    torchruntime.configure()
    if hasattr(torchruntime, "info"):
        torchruntime.info()

    # This dynamically sets the correct PYTHONPATH for Colab's Python version.
    python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
    if platform.system() != "Windows":
        os.environ["PYTHONPATH"] = str(Path(os.environ["INSTALL_ENV_DIR"]) / "lib" / python_version / "site-packages")

    os.environ["SD_UI_PATH"] = str(Path.cwd() / "ui")

    print(f"PYTHONPATH={os.environ.get('PYTHONPATH', 'Not Set')}")
    print(f"Python:  {shutil.which('python')}")
    print(f"Version: {platform.python_version()}")

    bind_ip = "127.0.0.1"
    listen_port = 9000
    if "net" in config and isinstance(config.get("net"), dict):
        print("Checking network settings")
        listen_port = config["net"].get("listen_port", 9000)
        print(f"Set listen port to {listen_port}")
        if config["net"].get("listen_to_network"):
            bind_ip = config["net"].get("bind_ip", "0.0.0.0")
            print(f"Set bind_ip to {bind_ip}")
    
    import uvicorn
    print("\nLaunching uvicorn\n")
    uvicorn.run(
        "main:server_api",
        port=listen_port,
        log_level="info",
        app_dir=os.environ["SD_UI_PATH"],
        host=bind_ip,
        access_log=False,
    )

# --- Main Execution Block ---
if __name__ == "__main__":
    if "--launch-uvicorn" in sys.argv:
        launch_uvicorn()
    else:
        update_modules()