"""
This script checks and installs the required modules.
Includes a robust, multi-step installation strategy to handle problematic
upstream dependencies like older versions of safetensors.
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
# Define the required packages and their target versions.
REQUIRED_PACKAGES = {
    # Core application library. Its old dependencies are the main issue.
    "sdkit": "2.0.22.8",
    # UI and Server
    "rich": "12.6.0",
    "uvicorn": "0.19.0",
    "fastapi": "0.115.6",
    "ruamel.yaml": "0.17.21",
    "sqlalchemy": "2.0.19",
    "python-multipart": "0.0.6",
    # Other dependencies
    "wandb": "0.17.2",
    "torchsde": "0.2.6",
    "basicsr": "1.4.2",
    "gfpgan": "1.3.8",
    "accelerate": "0.23.0",
}

# These packages are known to cause build issues if pinned to old versions.
# We will ensure modern, pre-compiled versions are installed.
MODERN_DEPS_TO_ENFORCE = {
    "safetensors": "0.4.3", # A known stable version with wheels
    "tokenizers": "0.15.2", # A known stable version with wheels
}

MODULES_TO_LOG = ["torch", "torchvision", "sdkit", "diffusers", "safetensors", "tokenizers"]

os_name = platform.system()

def get_package_version(package_name: str) -> str:
    try:
        return pkg_version(package_name)
    except PackageNotFoundError:
        return None

def run_pip_command(command: str, error_message: str):
    """Executes a pip command and handles errors."""
    print(f"> {command}")
    result = os.system(command)
    if result != 0:
        print(f"\nERROR: {error_message}")
        exit(1)

def update_modules():
    print("--- Checking environment dependencies ---")

    # Step 1: Ensure modern, compatible versions of problematic libraries are installed FIRST.
    # This pre-empts dependency resolution issues from sdkit.
    print("\n--- Step 1: Pre-installing modern core dependencies ---")
    for package, version in MODERN_DEPS_TO_ENFORCE.items():
        install_cmd = f'"{sys.executable}" -m pip install --upgrade "{package}=={version}"'
        run_pip_command(install_cmd, f"Failed to pre-install {package}")

    # Step 2: Install all other required packages, skipping sdkit for now.
    print("\n--- Step 2: Installing other project dependencies ---")
    for package, required_version in REQUIRED_PACKAGES.items():
        if package == "sdkit":  # We handle sdkit last
            continue
        
        current_version = get_package_version(package)
        if current_version is None or parse_version(current_version) != parse_version(required_version):
            use_pep517 = package in ("basicsr", "gfpgan")
            install_cmd = f'"{sys.executable}" -m pip install --upgrade "{package}=={required_version}"'
            if use_pep517:
                install_cmd += " --use-pep517"
            run_pip_command(install_cmd, f"Failed to install {package}")
        else:
            print(f"Package '{package}=={current_version}' is already correct. Skipping.")

    # Step 3: Install sdkit WITHOUT its dependencies, as we've handled them.
    print("\n--- Step 3: Installing sdkit with dependency resolution override ---")
    sdkit_version = REQUIRED_PACKAGES["sdkit"]
    install_cmd_no_deps = (
        f'"{sys.executable}" -m pip install --upgrade '
        f'"sdkit=={sdkit_version}" --no-dependencies'
    )
    run_pip_command(
        install_cmd_no_deps,
        "Failed to install sdkit package core. "
        "This might happen if its other dependencies are missing."
    )
    
    # Step 4: Run a final install to catch any other sub-dependencies sdkit might need,
    # but since safetensors is already installed, it won't be re-installed.
    print("\n--- Step 4: Verifying and installing remaining dependencies for sdkit ---")
    install_cmd_with_deps = f'"{sys.executable}" -m pip install --upgrade "sdkit=={sdkit_version}"'
    run_pip_command(install_cmd_with_deps, "Failed during final dependency check for sdkit.")

    print("\n--- Dependency check complete ---")
    for module_name in MODULES_TO_LOG:
        print(f"{module_name}: {get_package_version(module_name)}")


# --- Launcher and Utility Functions (Unchanged) ---
def get_config():
    config_directory = os.path.dirname(__file__)
    config_yaml = os.path.join(config_directory, "..", "config.yaml")
    if not os.path.isfile(config_yaml): config_yaml = os.path.join(config_directory, "config.yaml")
    if os.path.isfile(config_yaml):
        from ruamel.yaml import YAML
        yaml = YAML(typ="safe")
        with open(config_yaml, "r", encoding="utf-8") as file:
            return yaml.load(file) or {}
    return {}

def launch_uvicorn():
    config = get_config()
    print("\nEasy Diffusion installation complete, starting the server!\n")
    
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
        log_level="info",
        app_dir=os.environ["SD_UI_PATH"],
        access_log=False,
    )

if __name__ == "__main__":
    update_modules()

    if len(sys.argv) > 1 and sys.argv[1] == "--launch-uvicorn":
        launch_uvicorn()