"""
This script checks and installs the required modules.
FINAL VERSION FOR COLAB: Uses a multi-step installation process with --no-deps
to resolve the core dependency conflict between sdkit and safetensors.
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
    Installs dependencies in a specific order to bypass pip's resolution conflicts.
    """
    print("Starting multi-step installation process to resolve dependency conflicts...")
    
    # [STEP 1] Install PyTorch for CUDA
    print("\n[STEP 1/3] Installing PyTorch for CUDA...")
    os.system(f'"{sys.executable}" -m pip install --upgrade "torch" "torchvision" --index-url https://download.pytorch.org/whl/cu121')

    # [STEP 2] Install the problematic package (sdkit) WITHOUT its broken dependencies.
    print("\n[STEP 2/3] Installing sdkit (without its legacy dependencies)...")
    os.system(f'"{sys.executable}" -m pip install --upgrade --no-deps "sdkit==2.0.22.9"')

    # [STEP 3] Now, install all the OTHER correct, modern dependencies.
    print("\n[STEP 3/3] Installing all other modern dependencies...")
    packages = [
        "torchruntime",
        "stable-diffusion-sdkit==2.1.5",
        "diffusers>=0.28.0",
        "transformers>=0.28.0",
        "safetensors>=0.4.0", # This will satisfy the need for safetensors without conflict.
        "accelerate>=0.29.0",
        "fastapi",
        "uvicorn[standard]",
        "python-multipart",
        "pycloudflared",
        "gfpgan", "realesrgan", "piexif", "picklescan",
        "k-diffusion", "compel", "controlnet-aux", "invisible-watermark",
        "rich",
        "ruamel.yaml"
    ]
    package_list_str = " ".join([f'"{p}"' for p in packages])
    os.system(f'"{sys.executable}" -m pip install --upgrade {package_list_str}')

    print("\n--- Final Package Versions ---")
    for module_name in ["torch", "torchvision", "sdkit", "diffusers", "transformers", "safetensors"]:
        print(f"{module_name}: {version(module_name)}")
    print("----------------------------\n")

# --- Launcher Logic (No changes from previous version) ---
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
    import torchruntime
    config = get_config()
    pprint(config)
    with open("scripts/install_status.txt", "a") as f:
        f.write("sd_install_complete\n")

    print("\n\nEasy Diffusion installation complete, starting the server!\n\n")

    torchruntime.configure()
    if hasattr(torchruntime, "info"):
        torchruntime.info()

    python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
    if platform.system() != "Windows" and "INSTALL_ENV_DIR" in os.environ:
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

if __name__ == "__main__":
    if "--launch-uvicorn" in sys.argv:
        launch_uvicorn()
    else:
        update_modules()