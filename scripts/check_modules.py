"""
This script checks and installs the required modules.
Final Version: This script completely avoids installing the 'sdkit' package itself,
as its dependency metadata is broken. Instead, it manually installs all of
sdkit's necessary sub-dependencies with correct and compatible versions.
This provides a stable and functional environment without triggering the dependency trap.
"""
import os
import sys
import platform
from importlib.metadata import version as pkg_version, PackageNotFoundError
from packaging.version import parse as parse_version

# --- Configuration ---

# We are NOT installing 'sdkit'. Instead, we install its key components manually.
REQUIRED_PACKAGES = {
    # Core functionality packages from sdkit
    "stable-diffusion-sdkit": "2.1.5",
    "diffusers": "0.28.2",
    "k-diffusion": "0.0.12",
    "compel": "2.0.1",
    "controlnet-aux": "0.0.6",
    "invisible-watermark": "0.2.0",

    # Essential dependencies that were causing build failures
    "safetensors": None,  # None = install latest compatible version
    "tokenizers": None,   # None = install latest compatible version
    "accelerate": "0.23.0",

    # Other required UI and utility packages
    "gfpgan": "1.3.8",
    "realesrgan": "0.3.0",
    "piexif": "1.1.3",
    "picklescan": "0.0.28", # <-- *** 添加此行 ***
    "basicsr": "1.4.2",
    "rich": "12.6.0",
    "uvicorn": "0.19.0",
    "fastapi": "0.115.6",
    "ruamel.yaml": "0.17.21",
    "sqlalchemy": "2.0.19",
    "python-multipart": "0.0.6",
    "wandb": "0.17.2",
    "torchsde": "0.2.6",
}

# GPU-specific packages for performance
GPU_PACKAGES = {
    "xformers": "0.0.16",
}

MODULES_TO_LOG = ["torch", "torchvision", "stable-diffusion-sdkit", "diffusers", "accelerate", "xformers", "safetensors", "picklescan"]

# ... (以下所有函数保持不变，无需修改) ...

def get_package_version(package_name: str) -> str:
    # ... (代码不变)
    try:
        return pkg_version(package_name)
    except PackageNotFoundError:
        return None

def install_package(package_name: str, version_str: str = None, use_pep517: bool = False):
    # ... (代码不变)
    package_spec = f"{package_name}=={version_str}" if version_str else package_name
    install_cmd = f'"{sys.executable}" -m pip install --upgrade --no-cache-dir {package_spec}'
    if use_pep517:
        install_cmd += " --use-pep517"
    
    print(f"> {install_cmd}")
    result = os.system(install_cmd)
    if result != 0:
        fail(package_name)

def check_and_install_packages(packages: dict):
    # ... (代码不变)
    for package, required_version in packages.items():
        current_version = get_package_version(package)
        use_pep517 = package in ("basicsr", "gfpgan")

        if current_version is None:
            print(f"Package '{package}' not found. Installing {required_version or 'latest'}...")
            install_package(package, required_version, use_pep517)
        elif required_version and parse_version(current_version) != parse_version(required_version):
            print(f"Package '{package}' version mismatch. Found {current_version}, requires {required_version}. Re-installing...")
            install_package(package, required_version, use_pep517)
        else:
            print(f"Package '{package}=={current_version}' is already correct. Skipping.")

def update_modules():
    # ... (代码不变)
    print("--- Checking environment dependencies ---")
    if not get_package_version("torch"):
        import torchruntime
        torchruntime.install(["torch", "torchvision"])
    
    print("\n--- Installing all necessary components (bypassing sdkit package) ---")
    check_and_install_packages(REQUIRED_PACKAGES)

    try:
        import torch
        if torch.cuda.is_available():
            print("\n--- CUDA GPU detected. Checking GPU-specific packages... ---")
            check_and_install_packages(GPU_PACKAGES)
        else:
            print("\n--- No CUDA GPU detected. Skipping GPU-specific packages. ---")
    except ImportError:
        print("Could not import torch. Skipping GPU packages.")

    print("\n--- Dependency check complete ---")
    for module_name in MODULES_TO_LOG:
        version = get_package_version(module_name)
        print(f"{module_name}: {version if version else 'Not Installed'}")
    print("sdkit: Not Installed (by design)")


def fail(module_name):
    # ... (代码不变)
    print(f"\nERROR: Failed to install or upgrade '{module_name}'.")
    exit(1)


def get_config():
    # ... (代码不变)
    from pathlib import Path
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
    # ... (代码不变)
    from pathlib import Path
    import platform
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