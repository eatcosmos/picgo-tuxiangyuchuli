const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const http = require('http');
const https = require('https');

// 从HTTP调试URL获取实际的WebSocket URL
async function getWebSocketUrl(debugUrl) {
  return new Promise((resolve, reject) => {
    const protocol = debugUrl.startsWith('https') ? https : http;
    
    protocol.get(debugUrl, (res) => {
      let data = '';
      
      res.on('data', (chunk) => {
        data += chunk;
      });
      
      res.on('end', () => {
        try {
          const versionInfo = JSON.parse(data);
          if (versionInfo && versionInfo.webSocketDebuggerUrl) {
            resolve(versionInfo.webSocketDebuggerUrl);
          } else {
            reject(new Error('未能找到webSocketDebuggerUrl'));
          }
        } catch (error) {
          reject(new Error(`解析调试信息失败: ${error.message}`));
        }
      });
    }).on('error', (err) => {
      reject(new Error(`请求调试URL失败: ${err.message}`));
    });
  });
}

// 从文件读取调试URL
function getDebugUrl() {
  try {
    // 先尝试新的配置文件名
    const newConfigPath = path.join(__dirname, 'playwright_debug.json');
    if (fs.existsSync(newConfigPath)) {
      const config = JSON.parse(fs.readFileSync(newConfigPath, 'utf8'));
      return config.debugUrl || config.wsEndpoint;
    }
    
    // 向后兼容：尝试旧的配置文件名
    const oldConfigPath = path.join(__dirname, 'playwright_endpoint.json');
    if (fs.existsSync(oldConfigPath)) {
      const config = JSON.parse(fs.readFileSync(oldConfigPath, 'utf8'));
      return config.debugUrl || config.wsEndpoint;
    }
    
    throw new Error('找不到配置文件');
  } catch (error) {
    console.error('无法读取调试URL:', error.message);
    console.error('请确保playwright_server.py正在运行');
    process.exit(1);
  }
}

async function captureImageWithShadow(imagePath) {
  // 默认处理第一个命令行参数指定的图片，如果没有，则使用image.png
  const inputImagePath = imagePath || process.argv[2] || 'image.png';
  
  if (!fs.existsSync(inputImagePath)) {
    console.error(`错误: 文件 ${inputImagePath} 不存在!`);
    process.exit(1);
  }
  
  console.log(`处理图片: ${inputImagePath}`);
  
  // 获取调试URL
  const debugUrl = getDebugUrl();
  console.log(`获取调试信息: ${debugUrl}`);
  
  let browser;
  try {
    // 获取实际的WebSocket URL
    const wsEndpoint = await getWebSocketUrl(debugUrl);
    console.log(`连接到Chrome实例: ${wsEndpoint}`);
    
    // 连接到已运行的浏览器实例
    browser = await chromium.connectOverCDP(wsEndpoint);
    console.log('成功连接到Chrome实例');
    
    // 创建新的上下文和页面
    const context = await browser.newContext();
    const page = await context.newPage();
    
    // 获取本地HTML模板的绝对路径并导航到它
    const templatePath = `file://${path.join(__dirname, 'shadow_template.html')}`;
    await page.goto(templatePath);
    
    // 读取图片文件并转换为base64
    const imageBuffer = fs.readFileSync(inputImagePath);
    const base64Image = imageBuffer.toString('base64');
    const imageSrc = `data:image/${path.extname(inputImagePath).substring(1)};base64,${base64Image}`;
    
    // 将图片加载到页面中
    await page.evaluate((src) => {
      return window.setImageSource(src);
    }, imageSrc);
    
    // 等待图片元素加载完成
    await page.waitForSelector('#targetImage', { state: 'attached' });
    
    // 获取图片容器的位置和尺寸
    const boundingBox = await page.locator('.image-container').boundingBox();
    
    // 截取图片（包含阴影效果）
    await page.screenshot({
      path: inputImagePath, // 保存到原文件名
      clip: {
        x: boundingBox.x,
        y: boundingBox.y,
        width: boundingBox.width,
        height: boundingBox.height
      }
    });
    
    console.log(`✅ 已成功添加阴影效果并保存到: ${inputImagePath}`);
    
    // 关闭页面和上下文，但不要关闭浏览器
    await page.close();
    await context.close();
    
    // 断开与浏览器的连接
    // 在某些Playwright版本中，connectOverCDP返回的browser对象使用close而不是disconnect
    if (typeof browser.disconnect === 'function') {
      await browser.disconnect();
    } else if (typeof browser.close === 'function') {
      await browser.close();
    } else {
      console.warn('警告: 无法找到断开连接的方法，这可能会导致资源泄漏');
    }
    
  } catch (error) {
    console.error('处理图片时出错:', error);
    // 确保在出错时也断开连接
    if (browser) {
      if (typeof browser.disconnect === 'function') {
        await browser.disconnect();
      } else if (typeof browser.close === 'function') {
        await browser.close();
      }
    }
    process.exit(1);
  }
}

// 执行主函数
captureImageWithShadow().catch(console.error); 