#!/usr/bin/env python
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
        script_path = r"C:\code\picgo\picgo-tuxiangyuchuli\playwright_server.py"
        
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
                        (f"进程已退出，返回码: {self.process.returncode}，5秒后重启", '')
                    )
                    time.sleep(5)  # 等待5秒后重启
                else:
                    break
            except Exception as e:
                servicemanager.LogErrorMsg(f"服务错误: {str(e)}")
                time.sleep(5)  # 出错后等待5秒再尝试

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(PlaywrightService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(PlaywrightService)
