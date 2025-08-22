"""
This script checks and installs the required modules.
Final Version: This script uses a forceful, no-dependencies installation
strategy to construct the environment precisely as required. It installs
a specific, known-good set of packages in a deliberate order, bypassing
pip's dependency resolver to avoid all conflicts caused by legacy packages.
"""
import os
import sys
import platform
from importlib.metadata import version as pkg_version, PackageNotFoundError
from packaging.version import parse as parse_version

# --- Configuration ---

# This is a complete, known-good "lockfile" of all necessary packages.
# We will install every single one of these using --no-dependencies to ensure
# no other versions are pulled in unexpectedly. The order is intentional.
KNOWN_GOOD_ENV = {
    # Critical build-level dependencies first, with modern versions
    "safetensors": "0.4.3",  # A modern, stable version
    "tokenizers": "0.15.2", # A modern, stable version

    # Core AI/ML libraries
    "transformers": "4.33.2",
    "diffusers": "0.28.2",
    "accelerate": "0.23.0",
    "k-diffusion": "0.0.12",
    "compel": "2.0.1",
    "einops": "0.3.0", # s-d-sdkit needs this old version
    "kornia": "0.6.0",  # s-d-sdkit needs this old version
    "open-clip-torch": "2.0.2",
    "pytorch-lightning": "1.4.2",
    "torchmetrics": "0.6.0",
    "opencv-python": "4.6.0.66",
    
    # Application layer
    "stable-diffusion-sdkit": "2.1.5",

    # UI and utility packages
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
    "realesrgan": "0.3.0",
    "piexif": "1.1.3",
    "picklescan": "0.0.28",
    "albumentations": "1.3.0",
    "omegaconf": "2.1.1",
    "test-tube": "0.7.5",
}

# GPU-specific packages for performance
GPU_PACKAGES = {
    "xformers": "0.0.16",
}

MODULES_TO_LOG = list(KNOWN_GOOD_ENV.keys()) + list(GPU_PACKAGES.keys())

def get_package_version(package_name: str) -> str:
    try:
        return pkg_version(package_name)
    except PackageNotFoundError:
        return None

def force_install_package(package_name: str, version_str: str):
    package_spec = f"{package_name}=={version_str}"
    # The --no-dependencies flag is the key to this entire strategy
    install_cmd = f'"{sys.executable}" -m pip install --upgrade --no-dependencies --no-cache-dir {package_spec}'
    
    print(f"> {install_cmd}")
    result = os.system(install_cmd)
    if result != 0:
        fail(package_name)

def update_modules():
    print("--- Checking environment dependencies using forceful installation strategy ---")

    if not get_package_version("torch"):
        import torchruntime
        torchruntime.install(["torch", "torchvision"])
    
    for package, required_version in KNOWN_GOOD_ENV.items():
        current_version = get_package_version(package)
        
        # We always reinstall if the version doesn't match exactly
        if str(current_version) != required_version:
            force_install_package(package, required_version)
        else:
            print(f"Package '{package}=={current_version}' is already correct. Skipping.")

    try:
        import torch
        if torch.cuda.is_available():
            print("\n--- CUDA GPU detected. Checking GPU-specific packages... ---")
            for package, required_version in GPU_PACKAGES.items():
                if str(get_package_version(package)) != required_version:
                    force_install_package(package, required_version)
                else:
                    print(f"Package '{package}=={get_package_version(package)}' is already correct. Skipping.")
        else:
            print("\n--- No CUDA GPU detected. Skipping GPU-specific packages. ---")
    except ImportError:
        print("Could not import torch. Skipping GPU packages.")

    print("\n--- Dependency check complete ---")
    for module_name in MODULES_TO_LOG:
        version = get_package_version(module_name)
        print(f"{module_name}: {version if version else 'Not Installed'}")

def fail(module_name):
    print(f"\nERROR: Failed to install or upgrade '{module_name}'.")
    exit(1)

# --- Launcher and Utility Functions (remain unchanged) ---
from pathlib import Path
import platform

def get_config():
    # ... (code remains the same)
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
    # ... (code remains the same)
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
        "main:server_api", port=listen_port, host=bind_ip, log_level="error",
        app_dir=os.environ["SD_UI_PATH"], access_log=False,
    )

if __name__ == "__main__":
    update_modules()

    if len(sys.argv) > 1 and sys.argv[1] == "--launch-uvicorn":
        launch_uvicorn()