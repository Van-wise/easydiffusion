"""
This script checks and installs the required modules.
MODIFIED VERSION: Most of the complex logic has been moved to the main Colab
notebook to prevent dependency conflicts. This script now only handles
a few safe packages and the final launch command.
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

os_name = platform.system()

# Most modules are now pre-installed in the Colab notebook.
# This list only contains safe, non-conflicting packages.
modules_to_check = {
    "rich": "12.6.0",
    "uvicorn": "0.19.0",
    "fastapi": "0.115.6",
    "ruamel.yaml": "0.17.21",
    "sqlalchemy": "2.0.19",
    "python-multipart": "0.0.6",
    "basicsr": "1.4.2",
    "gfpgan": "1.3.8",
}
modules_to_log = ["torchruntime", "torch", "torchvision", "sdkit", "stable-diffusion-sdkit", "diffusers", "transformers", "safetensors"]


def version(module_name: str) -> str:
    try:
        return pkg_version(module_name)
    except:
        return None

def install(module_name: str, module_version: str):
    install_cmd = f'"{sys.executable}" -m pip install --upgrade {module_name}=={module_version}'
    if module_name in ("basicsr", "gfpgan"):
        install_cmd += " --use-pep517"
    print(">", install_cmd)
    os.system(install_cmd)

def update_modules():
    print("Running simplified module check...")
    for module_name, req_version in modules_to_check.items():
        if version(module_name) != req_version:
             try:
                install(module_name, req_version)
             except:
                traceback.print_exc()
                fail(module_name)

    print("\n--- Final Package Versions ---")
    for module_name in modules_to_log:
        print(f"{module_name}: {version(module_name)}")
    print("----------------------------\n")


def fail(module_name):
    print(f"Error installing {module_name}. Please check the logs.")
    exit(1)

### Launcher
def get_config():
    config_directory = os.path.dirname(__file__)  # this will be "scripts"
    config_yaml = os.path.join(config_directory, "..", "config.yaml")
    config = {}
    if os.path.isfile(config_yaml):
        from ruamel.yaml import YAML
        yaml = YAML(typ="safe")
        with open(config_yaml, "r", encoding="utf-8") as configfile:
            try:
                config = yaml.load(configfile)
            except Exception as e:
                print(e, file=sys.stderr)
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

    python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
    os.environ["PYTHONPATH"] = str(Path(os.environ.get("INSTALL_ENV_DIR", "/usr/local"), "lib", python_version, "site-packages"))
    os.environ["SD_UI_PATH"] = str(Path(Path.cwd(), "ui"))

    print(f"PYTHONPATH={os.environ['PYTHONPATH']}")
    print(f"Python:  {shutil.which('python')}")
    print(f"Version: {platform.python_version()}")

    bind_ip = "127.0.0.1"
    listen_port = 9000
    if "net" in config and isinstance(config["net"], dict):
        print("Checking network settings")
        listen_port = config["net"].get("listen_port", 9000)
        print(f"Set listen port to {listen_port}")
        if config["net"].get("listen_to_network"):
            bind_ip = config["net"].get("bind_ip", "0.0.0.0")
            print(f"Set bind_ip to {bind_ip}")

    print("\nLaunching uvicorn\n")
    import uvicorn

    uvicorn.run(
        "main:server_api",
        port=listen_port,
        log_level="error",
        app_dir=os.environ["SD_UI_PATH"],
        host=bind_ip,
        access_log=False,
    )

# --- Main execution logic ---
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--launch-uvicorn":
        launch_uvicorn()
    else:
        update_modules()