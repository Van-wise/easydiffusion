# @title (🔆) 启动 Easy Diffusion (最终版)
import os
import time
from IPython.display import display, HTML

# 忽略不必要的警告
import warnings
os.environ['PYTHONWARNINGS'] = 'ignore'
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
!git config --global advice.detachedHead false
warnings.filterwarnings("ignore")

# --- 1. 环境准备 ---
%cd /content
os.environ["INSTALL_ENV_DIR"] = "/usr/local"
#@markdown ### <font color="#11659a">选择仓库分支：</font>
_branch = "main" # @param ["main"]
start_time = time.time()

# --- 2. 克隆项目 ---
!git clone -q -b {_branch} https://github.com/Van-wise/easydiffusion.git sd-ui-files
print('✅ 项目克隆成功！')
main_dir = "/content/sd-ui-files"
%cd {main_dir}

# --- 3. 安装环境 (使用您仓库中最新的脚本) ---
print("\n⏳ 正在检查并安装环境，请稍候...")
!apt-get -qq -y update > /dev/null
!apt -y install -qq aria2 > /dev/null
!pip install -q pyngrok pycloudflared torchruntime==1.16.2 -U
!python ./scripts/check_modules.py

# --- 4. 下载模型 ---
print("\n⏳ 正在下载主模型...")
!aria2c --console-log-level=error -c -x 16 -s 16 -k 1M -d /content/models/stable-diffusion -o chilloutmix_NiPrunedFp32Fix-chonghui.safetensors https://huggingface.co/spaces/weo1101/111/resolve/main/chilloutmix_NiPrunedFp32Fix-inpainting.inpainting.safetensors
end_time = time.time()
print(f"✅ 环境安装与模型下载完成，耗时：{((end_time - start_time) / 60):.2f} 分钟.")

# --- 5. 配置网络穿透与启动 ---
import threading

# @markdown ### <font color="#11659a">选择网络服务</font>
# @markdown #### Ngrok (需要 Token):
ngrok_token = "" # @param {type:"string"}
# @markdown #### Cloudflare (推荐, 无需 Token):
use_cloudflare = True # @param {type:"boolean"}

def start_tunnel():
    # 等待 uvicorn 服务器启动
    # A simple way to check is to look for the log file and a startup message.
    log_file = "/content/output.log"
    while not os.path.exists(log_file) or "Application startup complete" not in open(log_file).read():
        time.sleep(1)

    print("\n🚀 服务器已启动！正在生成公共链接...")
    if ngrok_token:
        try:
            from pyngrok import ngrok
            ngrok.set_auth_token(ngrok_token)
            ngrok_tunnel = ngrok.connect(9000, "http")
            print("🔗 Ngrok 链接:", ngrok_tunnel)
        except Exception as e:
            print(f"❌ Ngrok 连接失败: {e}")

    if use_cloudflare:
        try:
            from pycloudflared import try_cloudflare
            cloudflare_url = try_cloudflare(9000, verbose=False)
            print("🔗 Cloudflare 链接:", cloudflare_url)
        except Exception as e:
            print(f"❌ Cloudflare 连接失败: {e}")

# 在后台线程中启动隧道
tunnel_thread = threading.Thread(target=start_tunnel, daemon=True)
tunnel_thread.start()

# 启动 Web UI，并将日志输出到文件
!python ./scripts/check_modules.py --launch-uvicorn 2>&1 | tee /content/output.log