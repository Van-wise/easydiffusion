"""
This script checks and installs the required modules.
Optimized for environments like Google Colab to avoid reinstalling existing packages.
"""
import os
import sys
import platform
import traceback
import shutil
from pathlib import Path
from pprint import pprint
import re
from importlib.metadata import version as pkg_version, PackageNotFoundError
from packaging.version import parse as parse_version

# --- Configuration ---
# Define the required packages and their specific versions for the project.
# We let sdkit manage its own dependencies like diffusers, transformers, etc.
REQUIRED_PACKAGES = {
    "sdkit": "2.0.22.8",
    "rich": "12.6.0",
    "uvicorn": "0.19.0",
    "fastapi": "0.115.6",
    "ruamel.yaml": "0.17.21",
    "sqlalchemy": "2.0.19",
    # WARNING: This version is known to conflict with modern versions of Gradio.
    # Keep it only if your project specifically requires it.
    "python-multipart": "0.0.6",
    "wandb": "0.17.2",
    "torchsde": "0.2.6",
    "basicsr": "1.4.2",
    "gfpgan": "1.3.8",
    # This is a dependency of sdkit, but we ensure a recent version to avoid issues.
    "accelerate": "0.23.0",
}

# List of packages whose versions we want to log at the end.
MODULES_TO_LOG = ["torch", "torchvision", "sdkit", "stable-diffusion-sdkit", "diffusers", "accelerate"]

os_name = platform.system()

def get_package_version(package_name: str) -> str:
    """Safely get the version of an installed package."""
    try:
        return pkg_version(package_name)
    except PackageNotFoundError:
        return None

def install_package(package_name: str, version_str: str = None, use_pep517: bool = False):
    """Install or upgrade a package using pip."""
    if version_str:
        package_spec = f"{package_name}=={version_str}"
    else:
        package_spec = package_name
    
    install_cmd = f'"{sys.executable}" -m pip install --upgrade {package_spec}'
    if use_pep517:
        install_cmd += " --use-pep517"
    
    print(f"> {install_cmd}")
    result = os.system(install_cmd)
    if result != 0:
        fail(package_name)

def update_modules():
    """
    Checks all required packages and installs/upgrades them only if they are
    missing or the version does not match.
    """
    print("--- Checking environment dependencies ---")

    # First, ensure torch is installed (it's fundamental)
    if not get_package_version("torch"):
        import torchruntime
        print("Torch not found. Installing torch and torchvision...")
        torchruntime.install(["torch", "torchvision"])

    # Check and install other packages if needed
    for package, required_version in REQUIRED_PACKAGES.items():
        current_version = get_package_version(package)

        # Special handling for older packages that might need PEP 517
        use_pep517 = package in ("basicsr", "gfpgan")

        if current_version is None:
            print(f"Package '{package}' not found. Installing version {required_version}...")
            install_package(package, required_version, use_pep517)
        elif parse_version(current_version) != parse_version(required_version):
            print(f"Package '{package}' version mismatch. Found {current_version}, requires {required_version}. Upgrading...")
            install_package(package, required_version, use_pep517)
        else:
            print(f"Package '{package}=={current_version}' is already installed and correct. Skipping.")
    
    print("\n--- Dependency check complete ---")
    for module_name in MODULES_TO_LOG:
        print(f"{module_name}: {get_package_version(module_name)}")


def fail(module_name):
    print(f"\nERROR: Failed to install or upgrade '{module_name}'.")
    # ... (rest of the fail message)
    exit(1)


# --- Launcher and Utility Functions (largely unchanged) ---

def get_config():
    # ... (this function can remain as it is)
    config_directory = os.path.dirname(__file__)
    config_yaml = os.path.join(config_directory, "..", "config.yaml")
    if not os.path.isfile(config_yaml): config_yaml = os.path.join(config_directory, "config.yaml") # legacy location
    if os.path.isfile(config_yaml):
        from ruamel.yaml import YAML
        yaml = YAML(typ="safe")
        with open(config_yaml, "r", encoding="utf-8") as file:
            return yaml.load(file) or {}
    return {}


def launch_uvicorn():
    config = get_config()
    print("\nEasy Diffusion installation complete, starting the server!\n")
    
    # Configure environment for UI
    install_env_dir = os.environ.get("INSTALL_ENV_DIR", "/usr/local")
    py_version_str = f"python{sys.version_info.major}.{sys.version_info.minor}"
    site_packages_path = Path(install_env_dir, "lib", py_version_str, "site-packages")
    
    os.environ["PYTHONPATH"] = str(site_packages_path)
    os.environ["SD_UI_PATH"] = str(Path.cwd() / "ui")
    
    print(f"PYTHONPATH={os.environ['PYTHONPATH']}")
    print(f"Python:     {sys.executable}")
    print(f"Version:    {platform.python_version()}")

    net_config = config.get("net", {})
    listen_port = net_config.get("listen_port", 9000)
    bind_ip = "0.0.0.0" if net_config.get("listen_to_network") else "127.0.0.1"

    print(f"Starting server on http://{bind_ip}:{listen_port}")
    
    import uvicorn
    uvicorn.run(
        "main:server_api",
        port=listen_port,
        host=bind_ip,
        log_level="error",
        app_dir=os.environ["SD_UI_PATH"],
        access_log=False,
    )

if __name__ == "__main__":
    update_modules()

    if len(sys.argv) > 1 and sys.argv[1] == "--launch-uvicorn":
        launch_uvicorn()