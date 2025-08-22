"""
This script launches the Easy Diffusion server.
"""
import os, sys
import shutil
import platform
from pathlib import Path
from pprint import pprint

# Removed all installation-related functions and variables
# The notebook now handles all dependency management.

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

    # We now assume torchruntime is installed and don't check for it
    # We also assume `easydiffusion` module can be found
    # as we rely on the notebook to do a proper installation.
    try:
        # Import torchruntime only if needed for information display
        import torchruntime
        torchruntime.configure()
        if hasattr(torchruntime, "info"):
            torchruntime.info()
    except ImportError:
        pass # The notebook already handles this.

    os_name = platform.system()
    if os_name == "Windows":
        os.environ["PYTHONPATH"] = str(Path(os.environ["INSTALL_ENV_DIR"], "lib", "site-packages"))
    else:
        # Note: We keep this line as a safeguard, but the notebook's pip install should
        # correctly place packages on the path.
        os.environ["PYTHONPATH"] = str(Path(os.environ["INSTALL_ENV_DIR"], "lib", "python3.12", "site-packages"))

    os.environ["SD_UI_PATH"] = str(Path(Path.cwd(), "ui"))

    print(f"PYTHONPATH={os.environ['PYTHONPATH']}")
    print(f"Python:  {shutil.which('python')}")
    print(f"Version: {platform.python_version()}")

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