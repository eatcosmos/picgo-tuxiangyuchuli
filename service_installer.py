#!/usr/bin/env python
import os
import sys
import argparse
import platform

def get_script_path():
    """获取当前脚本的绝对路径"""
    return os.path.dirname(os.path.abspath(__file__))

def install_windows_service():
    """在Windows上安装服务"""
    try:
        import win32serviceutil
        import win32service
        import win32event
        import servicemanager
        import socket
        import time
        from pathlib import Path
    except ImportError:
        print("错误: 缺少必要的库。请运行: pip install pywin32")
        return False

    # 获取脚本的绝对路径
    script_dir = get_script_path()
    playwright_server_path = os.path.join(script_dir, 'playwright_server.py')
    
    if not os.path.exists(playwright_server_path):
        print(f"错误: 找不到playwright_server.py文件: {playwright_server_path}")
        return False

    # 创建Windows服务包装脚本
    service_wrapper_path = os.path.join(script_dir, 'playwright_service_wrapper.py')
    
    with open(service_wrapper_path, 'w', encoding='utf-8') as f:
        f.write(f'''#!/usr/bin/env python
# -*- coding: utf-8 -*-

import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os
import subprocess
import time
import signal

class PlaywrightService(win32serviceutil.ServiceFramework):
    _svc_name_ = "PlaywrightChromeService"
    _svc_display_name_ = "Playwright Chrome Service"
    _svc_description_ = "提供持久化的Playwright Chrome实例服务"
    # 允许服务与桌面交互，这对于启动浏览器很重要
    _svc_interactive_process_ = True

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.is_running = False
        self.process = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.is_running = False
        if self.process:
            try:
                os.kill(self.process.pid, signal.SIGTERM)
                self.process.wait(timeout=10)
            except:
                if self.process:
                    self.process.kill()

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                             servicemanager.PYS_SERVICE_STARTED,
                             (self._svc_name_, ''))
        self.is_running = True
        self.main()

    def main(self):
        # 直接使用playwright_server.py的路径，而不是硬编码
        script_path = r"{playwright_server_path}"
        
        # 设置环境变量，使Chrome能够在服务环境中正常运行
        env = os.environ.copy()
        # 确保USERPROFILE环境变量存在，这对Chrome很重要
        if 'USERPROFILE' not in env:
            env['USERPROFILE'] = os.path.expanduser('~')
        
        while self.is_running:
            try:
                # 启动playwright_server.py，并传递环境变量
                self.process = subprocess.Popen(
                    [sys.executable, script_path],
                    env=env,
                    # 不要重定向输出，让它使用服务的日志
                    stdout=None,
                    stderr=None,
                    # 创建新的进程组，这样可以在需要时终止整个进程树
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
                
                # 等待服务停止信号或进程结束
                while self.is_running and self.process.poll() is None:
                    if win32event.WaitForSingleObject(self.hWaitStop, 1000) == win32event.WAIT_OBJECT_0:
                        break
                
                # 如果服务仍在运行但进程已结束，则重启进程
                if self.is_running and self.process.poll() is not None:
                    servicemanager.LogMsg(
                        servicemanager.EVENTLOG_WARNING_TYPE,
                        0,
                        (f"进程已退出，返回码: {{self.process.returncode}}，5秒后重启", '')
                    )
                    time.sleep(5)  # 等待5秒后重启
                else:
                    break
            except Exception as e:
                servicemanager.LogErrorMsg(f"服务错误: {{str(e)}}")
                time.sleep(5)  # 出错后等待5秒再尝试

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(PlaywrightService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(PlaywrightService)
''')

    print(f"Windows服务包装脚本已创建: {service_wrapper_path}")
    
    # 安装Windows服务
    import subprocess
    cmd = f'"{sys.executable}" "{service_wrapper_path}" install'
    print(f"正在安装Windows服务，请等待...")
    print(f"执行命令: {cmd}")
    
    try:
        subprocess.run(cmd, shell=True, check=True)
        print("服务安装成功!")
        print("您可以通过以下命令启动服务:")
        print(f"  {sys.executable} {service_wrapper_path} start")
        print("或在Windows服务管理器中启动'Playwright Chrome Service'")
        return True
    except subprocess.CalledProcessError as e:
        print(f"安装服务失败: {e}")
        return False

def install_linux_service():
    """在Linux上安装systemd服务"""
    service_path = '/etc/systemd/system/playwright-chrome.service'
    
    # 获取脚本的绝对路径
    script_dir = get_script_path()
    playwright_server_path = os.path.join(script_dir, 'playwright_server.py')
    
    if not os.path.exists(playwright_server_path):
        print(f"错误: 找不到playwright_server.py文件: {playwright_server_path}")
        return False
    
    # 获取当前Python解释器路径
    python_path = sys.executable
    
    # 创建systemd服务文件内容
    service_content = f'''[Unit]
Description=Playwright Chrome Service
After=network.target

[Service]
ExecStart={python_path} {playwright_server_path}
WorkingDirectory={script_dir}
Restart=always
RestartSec=10
User={os.environ.get('USER', 'root')}
Environment=DISPLAY=:0

[Install]
WantedBy=multi-user.target
'''
    
    # 需要root权限写入/etc目录
    if os.geteuid() != 0:
        print("错误: 需要root权限安装Linux服务")
        print(f"请尝试: sudo {python_path} {__file__} install")
        return False
    
    try:
        with open(service_path, 'w') as f:
            f.write(service_content)
        
        # 重新加载systemd配置
        os.system('systemctl daemon-reload')
        
        print("Linux服务安装成功!")
        print("您可以通过以下命令启动服务:")
        print("  sudo systemctl start playwright-chrome")
        print("设置开机自启:")
        print("  sudo systemctl enable playwright-chrome")
        return True
    except Exception as e:
        print(f"安装服务失败: {e}")
        return False

def uninstall_windows_service():
    """在Windows上卸载服务"""
    try:
        import win32serviceutil
    except ImportError:
        print("错误: 缺少必要的库。请运行: pip install pywin32")
        return False
    
    service_wrapper_path = os.path.join(get_script_path(), 'playwright_service_wrapper.py')
    
    if not os.path.exists(service_wrapper_path):
        print("错误: 服务包装脚本不存在，无法卸载服务")
        return False
    
    cmd = f'"{sys.executable}" "{service_wrapper_path}" remove'
    print(f"正在卸载Windows服务，请等待...")
    
    try:
        import subprocess
        subprocess.run(cmd, shell=True, check=True)
        print("服务卸载成功!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"卸载服务失败: {e}")
        return False

def uninstall_linux_service():
    """在Linux上卸载systemd服务"""
    service_path = '/etc/systemd/system/playwright-chrome.service'
    
    # 需要root权限
    if os.geteuid() != 0:
        print("错误: 需要root权限卸载Linux服务")
        print(f"请尝试: sudo {sys.executable} {__file__} uninstall")
        return False
    
    try:
        # 停止并禁用服务
        os.system('systemctl stop playwright-chrome')
        os.system('systemctl disable playwright-chrome')
        
        # 删除服务文件
        if os.path.exists(service_path):
            os.remove(service_path)
            os.system('systemctl daemon-reload')
            print("Linux服务卸载成功!")
            return True
        else:
            print("服务文件不存在，无需卸载")
            return True
    except Exception as e:
        print(f"卸载服务失败: {e}")
        return False

def check_service_status_windows():
    """检查Windows服务状态"""
    try:
        import win32serviceutil
        import win32service
    except ImportError:
        print("错误: 缺少必要的库。请运行: pip install pywin32")
        return False
    
    try:
        status = win32serviceutil.QueryServiceStatus("PlaywrightChromeService")[1]
        status_map = {
            win32service.SERVICE_STOPPED: "已停止",
            win32service.SERVICE_START_PENDING: "正在启动",
            win32service.SERVICE_STOP_PENDING: "正在停止",
            win32service.SERVICE_RUNNING: "正在运行",
            win32service.SERVICE_CONTINUE_PENDING: "正在继续",
            win32service.SERVICE_PAUSE_PENDING: "正在暂停",
            win32service.SERVICE_PAUSED: "已暂停"
        }
        print(f"服务状态: {status_map.get(status, f'未知({status})')}")
        
        if status == win32service.SERVICE_RUNNING:
            # 尝试连接到服务检查是否真正运行
            try:
                import requests
                response = requests.get("http://localhost:9222/json/version", timeout=2)
                if response.status_code == 200:
                    print("Chrome实例正在运行，可以连接")
                else:
                    print("警告: Chrome实例可能未正常运行")
            except:
                print("警告: 无法连接到Chrome实例")
        
        return True
    except Exception as e:
        print(f"服务不存在或查询失败: {e}")
        return False

def check_service_status_linux():
    """检查Linux服务状态"""
    try:
        import subprocess
        result = subprocess.run(['systemctl', 'is-active', 'playwright-chrome'], 
                               stdout=subprocess.PIPE, text=True)
        status = result.stdout.strip()
        
        if status == 'active':
            print("服务状态: 正在运行")
            # 尝试连接到服务检查是否真正运行
            try:
                import requests
                response = requests.get("http://localhost:9222/json/version", timeout=2)
                if response.status_code == 200:
                    print("Chrome实例正在运行，可以连接")
                else:
                    print("警告: Chrome实例可能未正常运行")
            except:
                print("警告: 无法连接到Chrome实例")
        else:
            print(f"服务状态: {status}")
        
        return True
    except Exception as e:
        print(f"检查服务状态失败: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Playwright Chrome服务安装工具")
    parser.add_argument('action', choices=['install', 'uninstall', 'status'],
                       help='要执行的操作: install(安装), uninstall(卸载), status(查看状态)')
    
    args = parser.parse_args()
    
    system = platform.system()
    
    if args.action == 'install':
        print(f"在{system}上安装Playwright Chrome服务...")
        if system == 'Windows':
            install_windows_service()
        elif system == 'Linux':
            install_linux_service()
        else:
            print(f"不支持的操作系统: {system}")
    
    elif args.action == 'uninstall':
        print(f"在{system}上卸载Playwright Chrome服务...")
        if system == 'Windows':
            uninstall_windows_service()
        elif system == 'Linux':
            uninstall_linux_service()
        else:
            print(f"不支持的操作系统: {system}")
    
    elif args.action == 'status':
        print(f"检查{system}上的Playwright Chrome服务状态...")
        if system == 'Windows':
            check_service_status_windows()
        elif system == 'Linux':
            check_service_status_linux()
        else:
            print(f"不支持的操作系统: {system}")

if __name__ == "__main__":
    main() 