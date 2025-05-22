# Playwright Chrome 持久化服务

这个项目提供了一个常驻内存的Playwright Chrome实例服务，让多个应用程序能共享使用，避免每次都启动新的浏览器实例，大大减少资源占用和启动时间。

## windows

 `npm run start-chrome # 会启动一个命令行启动一个Chrome界面，Playwright通过`

`enable-autostart`

`node playwright-screenshot.js`

## Linux

## 功能特点

- 常驻内存的Chrome实例，避免重复启动
- 自动检测和释放端口9222
- 浏览器窗口最小化启动，不干扰用户操作
- 浏览器状态监控，自动重启意外关闭的浏览器
- 提供简单的批处理脚本，方便启动和管理
- 支持开机自启动设置

## 安装和使用

### 前提条件

- Python 3.7+
- Node.js 14+
- Playwright Python库 (`pip install playwright`)
- PyWin32库 (`pip install pywin32`)

### 安装依赖

```bash
# 安装Node.js依赖
npm install

# 安装Python依赖
pip install playwright pywin32 psutil
```

### 启动服务

有两种方式可以启动服务：

#### 1. 使用批处理脚本（推荐）

双击 `start_playwright_service.bat`或运行：

```bash
npm run start-chrome
```

这将在后台启动Chrome实例，并保持运行。

#### 2. 直接运行Python脚本

```bash
python playwright_server.py
```

### 设置开机自启动

要使Chrome服务在Windows启动时自动运行：

```bash
# 启用开机自启动
npm run enable-autostart

# 禁用开机自启动
npm run disable-autostart
```

## 使用服务

一旦服务启动，其他应用程序可以通过WebSocket连接到Chrome实例。连接信息保存在 `playwright_debug.json`文件中。

### 示例：使用Node.js连接到服务

```javascript
const { chromium } = require('playwright');

async function connectToService() {
  // 从配置文件读取连接信息
  const config = require('./playwright_debug.json');
  const wsEndpoint = config.debugUrl;
  
  // 连接到浏览器实例
  const browser = await chromium.connectOverCDP(wsEndpoint);
  console.log('成功连接到Chrome实例');
  
  // 使用浏览器实例...
  const context = await browser.newContext();
  const page = await context.newPage();
  
  // 您的代码...
  
  // 完成后关闭上下文，但不要关闭浏览器
  await context.close();
  
  // 断开与浏览器的连接
  await browser.disconnect();
}
```

## 故障排除

### 端口9222已被占用

如果启动时提示端口9222已被占用，可以：

1. 使用任务管理器结束占用该端口的进程
2. 运行以下命令查看占用端口的进程：
   ```bash
   netstat -ano | findstr :9222
   ```

### 服务无法启动

如果服务无法启动，请检查：

1. 是否已安装所有依赖项
2. 是否有足够的权限运行脚本
3. 检查日志输出，查找错误信息

### 连接问题

如果其他应用程序无法连接到服务，请确认：

1. 服务是否正在运行（访问 http://localhost:9222/json/version）
2. 配置文件是否存在并包含正确的连接信息
3. 防火墙是否阻止了连接

## 许可证

MIT
