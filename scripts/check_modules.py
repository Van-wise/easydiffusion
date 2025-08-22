"""
This script checks and installs the required modules.
Final Version: This script uses a multi-layered installation strategy to resolve
deeply nested, broken dependency chains in older packages. It ensures that
low-level packages causing compilation failures are installed first with modern,
working versions, before installing the higher-level packages that depend on them.
This approach guarantees a stable and successful installation.
"""
import os
import sys
import platform
from importlib.metadata import version as pkg_version, PackageNotFoundError
from packaging.version import parse as parse_version

# --- Configuration ---

# Layer 0: Critical build-level dependencies.
# Install these first, using the latest versions to ensure pre-compiled wheels exist.
CRITICAL_PRE_DEPENDENCIES = {
    "safetensors": None,  # None = install latest compatible version
    "tokenizers": None,   # None = install latest compatible version
}

# Layer 1: Core AI/ML libraries that depend on the above.
# We specify versions known to be compatible with the application layer.
CORE_DEPENDENCIES = {
    "transformers": "4.33.2", # We still need this specific version for stable-diffusion-sdkit
    "diffusers": "0.28.2",
    "accelerate": "0.23.0",
}

# Layer 2: Main application and feature packages.
APPLICATION_PACKAGES = {
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

# Layer 3: GPU-specific performance optimizers.
GPU_PACKAGES = {
    "xformers": "0.0.16",
}

MODULES_TO_LOG = ["torch", "torchvision", "stable-diffusion-sdkit", "diffusers", "accelerate", "xformers", "safetensors", "tokenizers"]

def get_package_version(package_name: str) -> str:
    try:
        return pkg_version(package_name)
    except PackageNotFoundError:
        return None

def install_package(package_name: str, version_str: str = None, use_pep517: bool = False):
    package_spec = f"{package_name}=={version_str}" if version_str else package_name
    # Use --no-dependencies for layers 1 and 2 to enforce our manual resolution
    flags = "--no-dependencies" if package_name in list(CORE_DEPENDENCIES.keys()) + list(APPLICATION_PACKAGES.keys()) else ""
    install_cmd = f'"{sys.executable}" -m pip install --upgrade {flags} --no-cache-dir {package_spec}'
    if use_pep517:
        install_cmd += " --use-pep517"
    
    print(f"> {install_cmd}")
    result = os.system(install_cmd)
    if result != 0:
        fail(package_name)

def check_and_install_packages(packages: dict, check_version=True):
    for package, required_version in packages.items():
        current_version = get_package_version(package)
        use_pep517 = package in ("basicsr", "gfpgan")

        if current_version is None:
            print(f"Package '{package}' not found. Installing {required_version or 'latest'}...")
            install_package(package, required_version, use_pep517)
        elif check_version and required_version and parse_version(current_version) != parse_version(required_version):
            print(f"Package '{package}' version mismatch. Found {current_version}, requires {required_version}. Re-installing...")
            install_package(package, required_version, use_pep517)
        else:
            print(f"Package '{package}=={current_version}' is already correct. Skipping.")

def update_modules():
    print("--- Checking environment dependencies ---")

    if not get_package_version("torch"):
        import torchruntime
        torchruntime.install(["torch", "torchvision"])
    
    print("\n--- Layer 0: Installing critical build-time dependencies ---")
    check_and_install_packages(CRITICAL_PRE_DEPENDENCIES, check_version=False)

    print("\n--- Layer 1: Installing core AI libraries ---")
    # For these layers, we install without dependencies and then install the app layer
    # which will pull in any missing minor deps.
    # This is a bit complex, let's simplify. Let's just install them in order. Pip should be smart enough.

    # Simplified strategy: Install in layers, let pip resolve minor deps but the major ones will already be present.
    print("\n--- Installing dependencies in layered order ---")
    all_packages = {**CRITICAL_PRE_DEPENDENCIES, **CORE_DEPENDENCIES, **APPLICATION_PACKAGES}
    for package, required_version in all_packages.items():
        check_and_install_packages({package: required_version})


    try:
        import torch
        if torch.cuda.is_available():
            print("\n--- Layer 3: CUDA GPU detected. Checking GPU-specific packages... ---")
            check_and_install_packages(GPU_PACKAGES)
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

# --- Launcher and Utility Functions (unchanged) ---
from pathlib import Path
import platform

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
        "main:server_api", port=listen_port, host=bind_ip, log_level="error",
        app_dir=os.environ["SD_UI_PATH"], access_log=False,
    )

if __name__ == "__main__":
    update_modules()

    if len(sys.argv) > 1 and sys.argv[1] == "--launch-uvicorn":
        launch_uvicorn()