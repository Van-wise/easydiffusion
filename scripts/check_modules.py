# MODIFIED FOR PYTHON 3.12 COMPATIBILITY (V2 - FINAL)
"""
This script checks and installs the required modules.
This version includes a patch for both tokenizers and safetensors compilation issues on Python 3.12+.
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
modules_to_log = ["torchruntime", "torch", "torchvision", "sdkit", "stable-diffusion-sdkit", "diffusers", "transformers", "tokenizers", "safetensors"]

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
    # START: PYTHON 3.12 COMPATIBILITY PATCH (V2)
    # This block manually installs Python 3.12-compatible versions of problematic
    # libraries, bypassing the script's original, incompatible logic.
    # =================================================================================
    print("\nApplying Python 3.12 compatibility patch (V2)...")
    
    # 1. Install modern, pre-compiled versions of ALL blockers first.
    print("Patch Step 1/4: Installing compatible transformers, tokenizers, and safetensors...")
    os.system(f'"{sys.executable}" -m pip install --upgrade transformers tokenizers safetensors')

    # 2. Install the main packages, but IGNORE their outdated dependencies.
    print("Patch Step 2/4: Installing main packages (sdkit, stable-diffusion-sdkit) without their dependencies...")
    os.system(f'"{sys.executable}" -m pip install --upgrade --no-deps stable-diffusion-sdkit==2.1.5 sdkit==2.0.22.8')

    # 3. Now, install all other dependencies, letting pip resolve versions against our modern packages.
    print("Patch Step 3/4: Installing all other dependencies...")
    other_deps = [
        "gfpgan", "piexif", "realesrgan", "picklescan", "k-diffusion==0.0.12",
        "diffusers==0.28.2", "compel==2.0.1", "accelerate==0.23.0", "controlnet-aux==0.0.6",
        "invisible-watermark==0.2.0", "huggingface_hub==0.21.4", "albumentations==1.3.0",
        "opencv-python==4.6.0.66", "pytorch-lightning==1.4.2", "omegaconf==2.1.1",
        "test-tube>=0.7.5", "einops==0.3.0", "open-clip-torch==2.0.2",
        "torchmetrics==0.6.0", "ruamel.yaml"
    ]
    os.system(f'"{sys.executable}" -m pip install --upgrade {" ".join(other_deps)}')
    
    # 4. Final check on numpy version which can sometimes cause issues.
    print("Patch Step 4/4: Ensuring numpy version is compatible...")
    os.system(f'"{sys.executable}" -m pip install "numpy<2"')
    
    print("Python 3.12 compatibility patch applied successfully.\n")
    # =================================================================================
    # END: PYTHON 3.12 COMPATIBILITY PATCH
    # =================================================================================

    if version("torch") is None:
        torchruntime.install(["torch", "torchvision"])
    else:
        torch_version_str = version("torch")
        torch_version = version_str_to_tuple(torch_version_str)
        print(f"Current torch version: {torch_version} ({torch_version_str})")

    # The original loop is mostly bypassed by our patch. We only run it for xformers.
    for module_name, allowed_versions in modules_to_check.items():
        if os.path.exists(f"src/{module_name}"):
            print(f"Skipping {module_name} update, since it's in developer/editable mode")
            continue

        allowed_versions, latest_version = get_allowed_versions(module_name, allowed_versions)
        requires_install = version(module_name) not in allowed_versions
        if requires_install:
            try:
                install(module_name, latest_version)
            except:
                traceback.print_exc()
                fail(module_name)

    # All original installation logic below is now disabled as it's handled by the patch.
    
    print("\n--- Final Package Versions ---")
    for module_name in modules_to_log:
        print(f"{module_name}: {version(module_name)}")
    print("----------------------------\n")

# Helper functions remain unchanged
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