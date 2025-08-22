"""
This script checks and installs the required modules.
MODIFIED FOR COLAB: The update_modules() function is DISABLED to prevent
dependency conflicts. All installations are now handled in the main notebook.
This script is now only used as a LAUNCHER.
"""

import os, sys
from importlib.metadata import version as pkg_version
import platform
import traceback
import shutil
from pathlib import Path
from pprint import pprint
import re
import torchruntime
from torchruntime.device_db import get_gpus

os_name = platform.system()

# All modules are installed in the notebook, these lists are for logging only.
modules_to_check = {}
modules_to_log = ["torchruntime", "torch", "torchvision", "sdkit", "stable-diffusion-sdkit", "diffusers", "transformers", "safetensors"]

def version(module_name: str) -> str:
    try: return pkg_version(module_name)
    except: return None

def update_modules():
    # ####################################################################
    # # CRITICAL MODIFICATION: DO NOTHING.
    # # The entire original function is disabled because it's broken
    # # in the Colab environment. All installations are handled outside.
    # ####################################################################
    print("Skipping internal module installation to use pre-installed environment.")
    print("\n--- Final Package Versions ---")
    for module_name in modules_to_log:
        print(f"{module_name}: {version(module_name)}")
    print("----------------------------\n")

def get_config():
    config_directory = os.path.dirname(__file__)
    config_yaml = os.path.join(config_directory, "..", "config.yaml")
    config = {}
    if os.path.isfile(config_yaml):
        try:
            from ruamel.yaml import YAML
            yaml = YAML(typ="safe")
            with open(config_yaml, "r", encoding="utf-8") as configfile:
                config = yaml.load(configfile)
        except Exception as e:
            print(f"Error loading config file: {e}", file=sys.stderr)
    return config if config is not None else {}

def launch_uvicorn():
    config = get_config()
    pprint(config)

    with open("scripts/install_status.txt", "a") as f:
        f.write("sd_install_complete\n")

    print("\n\nEasy Diffusion installation complete, starting the server!\n\n")

    torchruntime.configure()
    if hasattr(torchruntime, "info"):
        torchruntime.info()

    # CRITICAL FIX for Colab Python version
    python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
    if os_name != "Windows":
        os.environ["PYTHONPATH"] = str(Path(os.environ["INSTALL_ENV_DIR"], "lib", python_version, "site-packages"))

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

    # The original script had an incorrect os.chdir() here, it has been removed.

    print("\nLaunching uvicorn\n")
    import uvicorn

    uvicorn.run(
        "main:server_api",
        port=listen_port,
        log_level="info",
        app_dir=os.environ["SD_UI_PATH"],
        host=bind_ip,
        access_log=False,
    )

# This is the main execution block
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--launch-uvicorn":
        launch_uvicorn()
    else:
        # If run without arguments, it will now do nothing harmful.
        update_modules()