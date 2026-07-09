const { app, BrowserWindow, Menu, shell, dialog } = require('electron');
const path = require('path');

// Default URL — 本地服务或公网
const DEFAULT_URL = 'https://autoevoai.com';
let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 860,
    minWidth: 900,
    minHeight: 600,
    icon: path.join(__dirname, 'icon.png'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      spellcheck: true,
    },
    titleBarStyle: 'default',
    backgroundColor: '#0f0f1a',
    show: false,
  });

  // 加载主页面
  mainWindow.loadURL(DEFAULT_URL);

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  // 外部链接用系统浏览器打开
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('https://') || url.startsWith('http://')) {
      shell.openExternal(url);
    }
    return { action: 'deny' };
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// 菜单
const menuTemplate = [
  {
    label: '文件',
    submenu: [
      {
        label: '刷新',
        accelerator: 'CmdOrCtrl+R',
        click: () => { if (mainWindow) mainWindow.reload(); }
      },
      {
        label: '开发者工具',
        accelerator: 'F12',
        click: () => { if (mainWindow) mainWindow.webContents.toggleDevTools(); }
      },
      { type: 'separator' },
      { role: 'quit', label: '退出' }
    ]
  },
  {
    label: '视图',
    submenu: [
      {
        label: '全屏',
        accelerator: 'F11',
        click: () => { if (mainWindow) mainWindow.setFullScreen(!mainWindow.isFullScreen()); }
      },
      { role: 'togglefullscreen', label: '切换全屏' }
    ]
  },
  {
    label: '帮助',
    submenu: [
      {
        label: '关于 AUTO-EVO-AI',
        click: () => {
          dialog.showMessageBox(mainWindow, {
            type: 'info',
            title: '关于 AUTO-EVO-AI',
            message: 'AUTO-EVO-AI V0.1',
            detail: '桌面客户端 v1.0.0\n全栈AI Agent操作系统\n500+模块 | 457技能 | 9种蒸馏',
          });
        }
      }
    ]
  }
];

const menu = Menu.buildFromTemplate(menuTemplate);
Menu.setApplicationMenu(menu);

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  app.quit();
});

app.on('activate', () => {
  if (mainWindow === null) createWindow();
});
