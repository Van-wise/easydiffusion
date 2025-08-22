"""
This script checks and installs the required modules.
Optimized for environments like Google Colab to avoid reinstalling existing packages.
It uses a dependency pre-installation strategy to bypass issues in sdkit's dependency chain.
"""
import os
import sys
import platform
import traceback
import shutil
from pathlib import Path
from importlib.metadata import version as pkg_version, PackageNotFoundError
from packaging.version import parse as parse_version

# --- Configuration ---

# Step 1: Pre-install problematic or core dependencies.
# We explicitly install the latest safetensors to override sdkit's broken dependency.
PRE_INSTALL_PACKAGES = {
    # Override sdkit's dependency on the broken 0.3.3 version
    "safetensors": None, # `None` means install the latest compatible version
    "tokenizers": None,  # Similarly, let pip choose the best version
    "accelerate": "0.23.0",
    "diffusers": "0.28.2", # A known compatible version for sdkit 2.0.22.8
}

# Step 2: Install the main application packages.
# sdkit is installed AFTER its problematic dependencies are already in place.
REQUIRED_PACKAGES = {
    "sdkit": "2.0.22.8",
    "stable-diffusion-sdkit": "2.1.5",
    "rich": "12.6.0",
    "uvicorn": "0.19.0",
    "fastapi": "0.115.6",
    "ruamel.yaml": "0.17.21",
    "sqlalchemy": "2.0.19",
    "python-multipart": "0.0.6",
    "wandb": "0.17.2",
    "torchsde": "0.2.6",
    "basicsr": "1.4.2",
    "gfpgan": "1.3.8",
}

# Step 3: GPU-specific packages.
GPU_PACKAGES = {
    "xformers": "0.0.16",
}

MODULES_TO_LOG = ["torch", "torchvision", "sdkit", "stable-diffusion-sdkit", "diffusers", "accelerate", "xformers", "safetensors", "tokenizers"]

def get_package_version(package_name: str) -> str:
    try:
        return pkg_version(package_name)
    except PackageNotFoundError:
        return None

def install_package(package_name: str, version_str: str = None, use_pep517: bool = False):
    package_spec = f"{package_name}=={version_str}" if version_str else package_name
    install_cmd = f'"{sys.executable}" -m pip install --upgrade {package_spec}'
    if use_pep517:
        install_cmd += " --use-pep517"
    
    print(f"> {install_cmd}")
    result = os.system(install_cmd)
    if result != 0:
        fail(package_name)

def check_and_install_packages(packages: dict):
    for package, required_version in packages.items():
        current_version = get_package_version(package)
        use_pep517 = package in ("basicsr", "gfpgan")

        if current_version is None:
            print(f"Package '{package}' not found. Installing {required_version or 'latest'}...")
            install_package(package, required_version, use_pep517)
        elif required_version and parse_version(current_version) != parse_version(required_version):
            print(f"Package '{package}' version mismatch. Found {current_version}, requires {required_version}. Upgrading...")
            install_package(package, required_version, use_pep517)
        else:
            print(f"Package '{package}=={current_version}' is already correct. Skipping.")

def update_modules():
    print("--- Checking environment dependencies ---")

    if not get_package_version("torch"):
        import torchruntime
        print("Torch not found. Installing torch and torchvision...")
        torchruntime.install(["torch", "torchvision"])
    
    print("\n--- Step 1: Pre-installing core dependencies to avoid conflicts ---")
    check_and_install_packages(PRE_INSTALL_PACKAGES)
    
    print("\n--- Step 2: Installing main application packages ---")
    check_and_install_packages(REQUIRED_PACKAGES)

    try:
        import torch
        if torch.cuda.is_available():
            print("\n--- Step 3: CUDA GPU detected. Checking GPU-specific packages... ---")
            check_and_install_packages(GPU_PACKAGES)
        else:
            print("\n--- No CUDA GPU detected. Skipping GPU-specific packages (xformers). ---")
    except ImportError:
        print("Could not import torch to check for GPU. Skipping GPU packages.")

    print("\n--- Dependency check complete ---")
    for module_name in MODULES_TO_LOG:
        version = get_package_version(module_name)
        print(f"{module_name}: {version if version else 'Not Installed'}")


def fail(module_name):
    print(f"\nERROR: Failed to install or upgrade '{module_name}'.")
    exit(1)

# --- Launcher and Utility Functions (remain unchanged) ---
def get_config():
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