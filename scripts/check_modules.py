"""
This script checks and installs the required modules.
"""
import os, sys
from importlib.metadata import version as pkg_version
import platform
import traceback
import shutil
from pathlib import Path
from pprint import pprint
import re
# 移除顶层导入，使其在函数中按需导入
# import torchruntime
# from torchruntime.device_db import get_gpus

os_name = platform.system()

modules_to_check = {
    # 移除setuptools, diffusers, huggingface-hub, uvicorn, python-multipart等
    # 这些库在Colab代码中手动安装，以解决版本冲突
    "rich": "12.6.0",
    "fastapi": "0.115.6",
    "ruamel.yaml": "0.17.21",
    "sqlalchemy": "2.0.19",
    "wandb": "0.17.2",
    "torchsde": "0.2.6",
    "basicsr": "1.4.2",
    "gfpgan": "1.3.8",
}
modules_to_log = ["torchruntime", "torch", "torchvision", "sdkit", "stable-diffusion-sdkit", "diffusers", "huggingface-hub", "uvicorn", "python-multipart"]

BLACKWELL_DEVICES = re.compile(r"\b(?:5060|5070|5080|5090)\b")

def version(module_name: str) -> str:
    try:
        return pkg_version(module_name)
    except:
        return None

def install(module_name: str, module_version: str, index_url=None):
    install_cmd = f'"{sys.executable}" -m pip install --upgrade {module_name}=={module_version}'

    if index_url:
        install_cmd += f" --index-url {index_url}"
    if module_name == "sdkit" and version("sdkit") is not None:
        install_cmd += " -q"
    if module_name in ("basicsr", "gfpgan"):
        install_cmd += " --use-pep517"
    
    print(">", install_cmd)
    os.system(install_cmd)

def update_modules():
    import torchruntime
    from torchruntime.device_db import get_gpus

    if version("torch") is None:
        torchruntime.install(["torch", "torchvision"])
    else:
        torch_version_str = version("torch")
        torch_version = version_str_to_tuple(torch_version_str)
        is_cpu_torch = "+" not in torch_version_str
        print(f"Current torch version: {torch_version} ({torch_version_str})")
        if torch_version < (2, 7) or is_cpu_torch:
            gpu_infos = get_gpus()
            device_names = set(gpu.device_name for gpu in gpu_infos)
            if any(BLACKWELL_DEVICES.search(device_name) for device_name in device_names):
                if sys.version_info < (3, 9):
                    print(
                        "\n###################################\n"
                        "NVIDIA 50xx series of graphics cards detected!\n\n"
                        "To use this graphics card, please install the latest version of Easy Diffusion from: https://github.com/easydiffusion/easydiffusion#installation"
                        "\n###################################\n"
                    )
                    sys.exit()
                else:
                    print("Upgrading torch to support NVIDIA 50xx series of graphics cards")
                    torchruntime.install(["--force", "--upgrade", "torch", "torchvision"])

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
            else:
                if version(module_name) != latest_version:
                    print(
                        f"WARNING! Tried to install {module_name}=={latest_version}, but the version is still {version(module_name)}!"
                    )

    # 移除sdkit和diffusers的特殊处理，将其交由Colab代码中的pip指令管理
    # 移除accelerate的特殊处理，将其交由pip管理
    # 移除过时的sdkit_deps列表

    for module_name in modules_to_log:
        print(f"{module_name}: {version(module_name)}")


def _install(module_name, module_version=None):
    if module_version is None:
        install_cmd = f'"{sys.executable}" -m pip install {module_name}'
    else:
        install_cmd = f'"{sys.executable}" -m pip install --upgrade {module_name}=={module_version}'
    print(">", install_cmd)
    os.system(install_cmd)

def install_pkg_if_necessary(pkg_name, required_version):
    if os.path.exists(f"src/{pkg_name}"):
        print(f"Skipping {pkg_name} update, since it's in developer/editable mode")
        return

    pkg_version = version(pkg_name)
    if pkg_version != required_version:
        _install(pkg_name, required_version)

def version_str_to_tuple(ver_str):
    ver_str = ver_str.split("+")[0]
    ver_str = re.sub("[^0-9.]", "", ver_str)
    ver = ver_str.split(".")
    return tuple(map(int, ver))

### utilities
def get_allowed_versions(module_name: str, allowed_versions: tuple):
    allowed_versions = (allowed_versions,) if isinstance(allowed_versions, str) else allowed_versions
    latest_version = allowed_versions[-1]
    return allowed_versions, latest_version

def fail(module_name):
    print(
        f"""Error installing {module_name}. Sorry about that, please try to:
1. Run this installer again.
2. If that doesn't fix it, please try the common troubleshooting steps at https://github.com/easydiffusion/easydiffusion/wiki/Troubleshooting
3. If those steps don't help, please copy *all* the error messages in this window, and ask the community at https://discord.com/invite/u9yhsFmEkB
4. If that doesn't solve the problem, please file an issue at https://github.com/easydiffusion/easydiffusion/issues
Thanks!"""
    )
    exit(1)


### Launcher
def get_config():
    config_directory = os.path.dirname(__file__)
    config_yaml = os.path.join(config_directory, "..", "config.yaml")
    config_json = os.path.join(config_directory, "config.json")

    config = None
    config_legacy_yaml = os.path.join(config_directory, "config.yaml")
    if os.path.isfile(config_legacy_yaml):
        shutil.move(config_legacy_yaml, config_yaml)

    if os.path.isfile(config_yaml):
        from ruamel.yaml import YAML
        yaml = YAML(typ="safe")
        with open(config_yaml, "r") as configfile:
            try:
                config = yaml.load(configfile)
            except Exception as e:
                print(e, file=sys.stderr)
    elif os.path.isfile(config_json):
        import json
        with open(config_json, "r") as configfile:
            try:
                config = json.load(configfile)
            except Exception as e:
                print(e, file=sys.stderr)

    if config is None:
        config = {}
    return config

def launch_uvicorn():
    config = get_config()
    pprint(config)

    with open("scripts/install_status.txt", "a") as f:
        f.write("sd_weights_downloaded\n")
        f.write("sd_install_complete\n")

    print("\n\nEasy Diffusion installation complete, starting the server!\n\n")

    import torchruntime
    torchruntime.configure()
    if hasattr(torchruntime, "info"):
        torchruntime.info()

    if os_name == "Windows":
        os.environ["PYTHONPATH"] = str(Path(os.environ["INSTALL_ENV_DIR"], "lib", "site-packages"))
    else:
        os.environ["PYTHONPATH"] = str(Path(os.environ["INSTALL_ENV_DIR"], "lib", "python3.12", "site-packages"))
    os.environ["SD_UI_PATH"] = str(Path(Path.cwd(), "ui"))

    print(f"PYTHONPATH={os.environ['PYTHONPATH']}")
    print(f"Python:  {shutil.which('python')}")
    print(f"Version: {platform. python_version()}")

    bind_ip = "127.0.0.1"
    listen_port = 9000
    if "net" in config:
        print("Checking network settings")
        if "listen_port" in config["net"]:
            listen_port = config["net"]["listen_port"]
            print("Set listen port to ", listen_port)
        if "listen_to_network" in config["net"] and config["net"]["listen_to_network"] == True:
            if "bind_ip" in config["net"]:
                bind_ip = config["net"]["bind_ip"]
            else:
                bind_ip = "0.0.0.0"
            print("Set bind_ip to ", bind_ip)

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