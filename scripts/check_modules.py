"""
This script checks and installs the required modules.
"""
import os, sys
from importlib.metadata import version as pkg_version
import platform
import shutil
from pathlib import Path
from pprint import pprint
import re

os_name = platform.system()

modules_to_check = {
    "ruamel.yaml": "0.17.21",
    "sqlalchemy": "2.0.19",
    "wandb": "0.17.2",
    "torchsde": "0.2.6",
    "basicsr": "1.4.2",
    "gfpgan": "1.3.8",
}

modules_to_log = ["torchruntime", "torch", "torchvision", "sdkit", "stable-diffusion-sdkit", "diffusers", "huggingface-hub", "uvicorn", "python-multipart", "ruamel.yaml"]


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
    # 这一部分是关键，我们只检查并修复最核心的依赖，但主要的安装工作已经交给Colab代码
    print("Checking modules...")
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

    for module_name in modules_to_log:
        print(f"{module_name}: {version(module_name)}")


def version_str_to_tuple(ver_str):
    ver_str = ver_str.split("+")[0]
    ver_str = re.sub("[^0-9.]", "", ver_str)
    ver = ver_str.split(".")
    return tuple(map(int, ver))

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
    # ... (此函数恢复了部分逻辑，但不再尝试安装)
    config = get_config()
    pprint(config)

    with open("scripts/install_status.txt", "a") as f:
        f.write("sd_weights_downloaded\n")
        f.write("sd_install_complete\n")

    print("\n\nEasy Diffusion installation complete, starting the server!\n\n")

    try:
        import torchruntime
        torchruntime.configure()
        if hasattr(torchruntime, "info"):
            torchruntime.info()
    except ImportError:
        print("Warning: torchruntime module not found. The server may not function correctly without it.")

    os_name = platform.system()
    if os_name == "Windows":
        os.environ["PYTHONPATH"] = str(Path(os.environ["INSTALL_ENV_DIR"], "lib", "site-packages"))
    else:
        # 这一行我们已经在Colab代码中手动设置了，这里作为保险
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

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--launch-uvicorn":
        launch_uvicorn()