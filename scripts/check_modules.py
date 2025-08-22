# MODIFIED FOR PYTHON 3.12 COMPATIBILITY (V3 - FINAL)
"""
This script checks and installs the required modules.
This final version resolves the 'clear_device_cache' ImportError by carefully
managing the 'accelerate' and 'huggingface-hub' package versions.
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

# We will handle all problematic modules manually in our patch.
modules_to_check = {
    "xformers": "0.0.16",
}
modules_to_log = ["torchruntime", "torch", "torchvision", "sdkit", "stable-diffusion-sdkit", "diffusers", "transformers", "tokenizers", "safetensors", "accelerate", "huggingface-hub"]

BLACKWELL_DEVICES = re.compile(r"\b(?:5060|5070|5080|5090)\b")

def version(module_name: str) -> str:
    try:
        return pkg_version(module_name)
    except:
        return None

def install(module_name: str, module_version: str, index_url=None, extra_args=""):
    install_cmd = f'"{sys.executable}" -m pip install --upgrade {module_name}=={module_version} {extra_args}'
    if index_url:
        install_cmd += f" --index-url {index_url}"
    print(">", install_cmd)
    os.system(install_cmd)

def update_modules():
    # =================================================================================
    # START: PYTHON 3.12 COMPATIBILITY PATCH (V3 - FINAL)
    # =================================================================================
    print("\nApplying Python 3.12 compatibility patch (V3 - Final)...")
    
    # 1. Install modern, pre-compiled versions of the initial blockers.
    print("Patch Step 1/5: Installing compatible transformers, tokenizers, and safetensors...")
    os.system(f'"{sys.executable}" -m pip install --upgrade "transformers>=4.33.2" "tokenizers>=0.15.0" "safetensors>=0.4.0"')

    # 2. Install the main packages, but IGNORE their outdated dependencies.
    print("Patch Step 2/5: Installing main packages (sdkit, stable-diffusion-sdkit) without their dependencies...")
    os.system(f'"{sys.executable}" -m pip install --upgrade --no-deps stable-diffusion-sdkit==2.1.5 sdkit==2.0.22.8')
    
    # 3. CRITICAL FIX: Install a newer version of 'accelerate' to resolve the ImportError,
    #    while forcing 'huggingface-hub' and 'transformers' to the versions sdkit can tolerate.
    print("Patch Step 3/5: Upgrading 'accelerate' and locking critical dependency versions...")
    os.system(f'"{sys.executable}" -m pip install --upgrade accelerate "huggingface_hub==0.21.4" "transformers==4.33.2"')

    # 4. Install all other dependencies.
    print("Patch Step 4/5: Installing all other remaining dependencies...")
    other_deps = [
        "gfpgan", "piexif", "realesrgan", "picklescan", "k-diffusion==0.0.12",
        "diffusers==0.28.2", "compel==2.0.1", "controlnet-aux==0.0.6",
        "invisible-watermark==0.2.0", "albumentations==1.3.0",
        "opencv-python==4.6.0.66", "pytorch-lightning==1.4.2", "omegaconf==2.1.1",
        "test-tube>=0.7.5", "einops==0.3.0", "open-clip-torch==2.0.2",
        "torchmetrics==0.6.0", "ruamel.yaml"
    ]
    os.system(f'"{sys.executable}" -m pip install --upgrade {" ".join(other_deps)}')
    
    # 5. Final check on numpy version.
    print("Patch Step 5/5: Ensuring numpy version is compatible...")
    os.system(f'"{sys.executable}" -m pip install "numpy<2"')
    
    print("Python 3.12 compatibility patch applied successfully.\n")
    # =================================================================================
    # END: PYTHON 3.12 COMPATIBILITY PATCH
    # =================================================================================

    if version("torch") is None:
        torchruntime.install(["torch", "torchvision"])
    else:
        print(f"Current torch version: {version('torch')}")

    for module_name, allowed_versions in modules_to_check.items():
        if os.path.exists(f"src/{module_name}"):
            print(f"Skipping {module_name} update, since it's in developer/editable mode")
            continue
        allowed_versions, latest_version = get_allowed_versions(module_name, allowed_versions)
        if version(module_name) not in allowed_versions:
            try:
                install(module_name, latest_version)
            except:
                traceback.print_exc()
                fail(module_name)
    
    print("\n--- Final Package Versions ---")
    for module_name in modules_to_log:
        print(f"{module_name}: {version(module_name)}")
    print("----------------------------\n")

# Helper functions and Launcher remain the same
def _install(module_name, module_version=None):
    if module_version is None:
        install_cmd = f'"{sys.executable}" -m pip install {module_name}'
    else:
        install_cmd = f'"{sys.executable}" -m pip install --upgrade {module_name}=={module_version}'
    print(">", install_cmd)
    os.system(install_cmd)

def version_str_to_tuple(ver_str):
    if ver_str is None: return (0, 0, 0)
    ver_str = ver_str.split("+")[0]
    ver_str = re.sub("[^0-9.]", "", ver_str)
    ver = ver_str.split(".")
    return tuple(map(int, ver))

def get_allowed_versions(module_name: str, allowed_versions: tuple):
    allowed_versions = (allowed_versions,) if isinstance(allowed_versions, str) else allowed_versions
    latest_version = allowed_versions[-1]
    return allowed_versions, latest_version

def fail(module_name):
    print(f"Error installing {module_name}.")
    exit(1)

def get_config():
    config_directory = os.path.dirname(__file__)
    config_yaml = os.path.join(config_directory, "..", "config.yaml")
    config = {}
    if os.path.isfile(config_yaml):
        if version("ruamel.yaml") is None:
            os.system(f'"{sys.executable}" -m pip install ruamel.yaml')
        from ruamel.yaml import YAML
        yaml = YAML(typ="safe")
        with open(config_yaml, "r") as configfile:
            try:
                config = yaml.load(configfile)
            except Exception as e:
                print(e, file=sys.stderr)
    return config if config is not None else {}

def launch_uvicorn():
    config = get_config()
    print("\n--- Config ---")
    pprint(config)
    print("--------------\n")
    
    print("\n\nEasy Diffusion installation complete, starting the server!\n\n")

    torchruntime.configure()
    if hasattr(torchruntime, "info"):
        torchruntime.info()

    py_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
    os.environ["PYTHONPATH"] = str(Path(os.environ["INSTALL_ENV_DIR"], "lib", py_version, "site-packages"))
    os.environ["SD_UI_PATH"] = str(Path(Path.cwd(), "ui"))

    print(f"PYTHONPATH={os.environ['PYTHONPATH']}")
    print(f"Python:  {shutil.which('python')}")
    print(f"Version: {platform.python_version()}")

    bind_ip = "127.0.0.1"
    listen_port = 9000
    if "net" in config:
        if "listen_port" in config["net"]: listen_port = config["net"]["listen_port"]
        if config["net"].get("listen_to_network"): bind_ip = config["net"].get("bind_ip", "0.0.0.0")

    print(f"Will listen on {bind_ip}:{listen_port}")
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

update_modules()

if len(sys.argv) > 1 and sys.argv[1] == "--launch-uvicorn":
    launch_uvicorn()