from playwright.sync_api import sync_playwright
import os
import time
import json
import subprocess
import requests
import signal
import sys
import atexit
import socket
import psutil  # 需要安装: pip install psutil

# 配置文件路径，用于存储wsEndpoint
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'playwright_debug.json')
# 浏览器数据保存目录
USER_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'browser_data')
# 调试端口
DEBUG_PORT = 9222

def save_endpoint(ws_endpoint):
    """保存wsEndpoint到配置文件"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump({'debugUrl': ws_endpoint}, f)
    print(f"调试URL已保存到 {CONFIG_FILE}")

def is_port_in_use(port):
    """检查端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def find_process_by_port(port):
    """查找占用指定端口的进程"""
    for proc in psutil.process_iter(['pid', 'name', 'connections']):
        try:
            for conn in proc.connections(kind='inet'):
                if conn.laddr.port == port:
                    return proc
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass
    return None

def kill_process_on_port(port):
    """杀死占用指定端口的进程"""
    process = find_process_by_port(port)
    if process:
        print(f"发现端口 {port} 被进程 {process.pid} ({process.name()}) 占用")
        try:
            process.terminate()
            print(f"已发送终止信号到进程 {process.pid}")
            
            # 等待进程终止
            gone, alive = psutil.wait_procs([process], timeout=5)
            if alive:
                print(f"进程 {process.pid} 未响应终止信号，强制杀死")
                for p in alive:
                    p.kill()
            
            print(f"已成功释放端口 {port}")
            # 等待端口完全释放
            time.sleep(1)
            return True
        except Exception as e:
            print(f"终止进程时出错: {e}")
            return False
    else:
        print(f"未找到占用端口 {port} 的进程")
        return False

def is_browser_running():
    """检查浏览器是否在运行中"""
    try:
        # 尝试连接调试端口
        requests.get(f"http://localhost:{DEBUG_PORT}/json/version", timeout=1)
        return True
    except requests.RequestException:
        return False

def cleanup():
    """退出时清理资源"""
    print("\n清理资源...")
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)
        print("已删除配置文件")
    print("服务已停止")

def launch_browser(playwright):
    """启动浏览器并返回browser_process"""
    print("启动Chrome实例...")
    
    # 检查端口是否被占用，如果是，则杀死占用进程
    if is_port_in_use(DEBUG_PORT):
        print(f"端口 {DEBUG_PORT} 已被占用，尝试释放...")
        if not kill_process_on_port(DEBUG_PORT):
            print(f"警告: 无法释放端口 {DEBUG_PORT}，尝试继续启动...")
    
    # 使用launch_persistent_context而不是launch，这样可以保存浏览器状态
    browser_process = playwright.chromium.launch_persistent_context(
        user_data_dir=USER_DATA_DIR,
        headless=False,  # 非无头模式
        args=[
            f'--remote-debugging-port={DEBUG_PORT}',
            '--start-minimized',  # 最小化启动，但允许用户之后通过任务栏激活
        ]
    )
    
    # 构建调试URL
    debug_url = f"http://localhost:{DEBUG_PORT}/json/version"
    
    # 打印并保存连接信息
    print(f"\n{'='*50}")
    print(f"Chrome实例已启动!")
    print(f"调试地址: {debug_url}")
    print(f"其他脚本可以使用此地址连接到浏览器实例")
    print(f"{'='*50}\n")
    
    # 保存调试URL到配置文件
    save_endpoint(debug_url)
    
    return browser_process

def run_browser_server():
    """主函数，运行浏览器服务器"""
    print("启动持久化Playwright Chrome引擎服务...")
    
    # 注册清理函数
    atexit.register(cleanup)
    
    # 设置信号处理，以便优雅退出
    def signal_handler(sig, frame):
        print("\n接收到退出信号，正在关闭服务...")
        sys.exit(0)
    
    # 注册SIGINT和SIGTERM信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)
    
    # 检查间隔时间（秒）
    CHECK_INTERVAL = 1
    
    # 启动Playwright并保持活跃
    with sync_playwright() as p:
        # 首次启动浏览器
        browser_process = launch_browser(p)
        
        print(f"监控Chrome实例状态，每{CHECK_INTERVAL}秒检查一次，如果被关闭将自动重启...")
        print("按Ctrl+C退出服务")
        
        try:
            # 持续检查浏览器状态
            while True:
                if not is_browser_running():
                    print("检测到Chrome实例已关闭，正在重启...")
                    # 如果browser_process仍有引用，尝试关闭它
                    try:
                        browser_process.close()
                    except:
                        pass
                    # 重新启动浏览器
                    browser_process = launch_browser(p)
                
                # 每隔CHECK_INTERVAL秒检查一次
                time.sleep(CHECK_INTERVAL)
                
        except KeyboardInterrupt:
            print("\n接收到Ctrl+C，正在关闭服务...")
        except Exception as e:
            print(f"发生错误: {e}")
        finally:
            # 关闭浏览器
            try:
                browser_process.close()
                print("浏览器已关闭")
            except:
                pass

if __name__ == "__main__":
    run_browser_server()