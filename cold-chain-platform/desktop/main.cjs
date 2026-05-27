const { app, BrowserWindow, Menu, ipcMain, shell } = require("electron");
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");
const { URL } = require("node:url");

const FRONTEND_URL = "http://localhost:5173";
const API_HEALTH_URL = "http://localhost:8000/api/health";
const API_DIAGNOSTICS_URL = "http://localhost:8000/api/diagnostics";
const COMPOSE_PROJECT_NAME = "cold-chain-platform";

let mainWindow;
let booting = false;
let localApiProcess = null;
let localFrontendServer = null;

function resolveProjectRoot() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, "app");
  }
  return path.resolve(__dirname, "..");
}

const projectRoot = resolveProjectRoot();

function readEnvFile(filePath) {
  if (!fs.existsSync(filePath)) return {};
  const result = {};
  for (const line of fs.readFileSync(filePath, "utf8").split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#") || !trimmed.includes("=")) continue;
    const index = trimmed.indexOf("=");
    result[trimmed.slice(0, index)] = trimmed.slice(index + 1);
  }
  return result;
}

function send(channel, payload) {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send(channel, payload);
  }
}

function appendLog(message) {
  const line = `[${new Date().toLocaleTimeString()}] ${message}`;
  send("desktop-log", line);
}

function runCommand(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    appendLog(`执行：${command} ${args.join(" ")}`);
    const child = spawn(command, args, {
      cwd: options.cwd || projectRoot,
      shell: true,
      windowsHide: true,
      env: process.env
    });

    child.stdout.on("data", (chunk) => appendLog(chunk.toString("utf8").trim()));
    child.stderr.on("data", (chunk) => appendLog(chunk.toString("utf8").trim()));
    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`${command} 退出码 ${code}`));
      }
    });
  });
}

function contentType(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  if (ext === ".html") return "text/html; charset=utf-8";
  if (ext === ".js") return "text/javascript; charset=utf-8";
  if (ext === ".css") return "text/css; charset=utf-8";
  if (ext === ".json") return "application/json; charset=utf-8";
  if (ext === ".svg") return "image/svg+xml";
  if (ext === ".png") return "image/png";
  if (ext === ".jpg" || ext === ".jpeg") return "image/jpeg";
  return "application/octet-stream";
}

function proxyApi(req, res) {
  const target = new URL(req.url, "http://127.0.0.1:8000");
  const proxyReq = http.request(
    {
      hostname: "127.0.0.1",
      port: 8000,
      path: target.pathname + target.search,
      method: req.method,
      headers: req.headers
    },
    (proxyRes) => {
      res.writeHead(proxyRes.statusCode || 502, proxyRes.headers);
      proxyRes.pipe(res);
    }
  );
  proxyReq.on("error", () => {
    res.writeHead(502, { "content-type": "text/plain; charset=utf-8" });
    res.end("本地 API 尚未就绪");
  });
  req.pipe(proxyReq);
}

function startStaticFrontend() {
  if (localFrontendServer) return Promise.resolve();
  const distDir = path.join(projectRoot, "frontend", "dist");
  return new Promise((resolve, reject) => {
    localFrontendServer = http.createServer((req, res) => {
      if (req.url.startsWith("/api")) {
        proxyApi(req, res);
        return;
      }
      const requestPath = decodeURIComponent((req.url.split("?")[0] || "/").replace(/^\/+/, ""));
      const candidate = path.normalize(path.join(distDir, requestPath || "index.html"));
      const safePath = candidate.startsWith(distDir) && fs.existsSync(candidate) && fs.statSync(candidate).isFile()
        ? candidate
        : path.join(distDir, "index.html");
      res.writeHead(200, { "content-type": contentType(safePath) });
      fs.createReadStream(safePath).pipe(res);
    });
    localFrontendServer.once("error", reject);
    localFrontendServer.listen(5173, "127.0.0.1", () => {
      appendLog("本地前端服务已启动");
      resolve();
    });
  });
}

async function startLocalServices() {
  const dataDir = path.join(app.getPath("userData"), "local-runtime");
  fs.mkdirSync(dataDir, { recursive: true });
  const dbPath = path.join(dataDir, "cold_chain.sqlite").replace(/\\/g, "/");
  const envFile = readEnvFile(path.join(projectRoot, ".env"));
  const backendExe = path.join(projectRoot, "backend-local", "cold-chain-api.exe");
  const backendCwd = fs.existsSync(backendExe) ? path.dirname(backendExe) : path.join(projectRoot, "backend");
  const command = fs.existsSync(backendExe) ? backendExe : "python";
  const args = fs.existsSync(backendExe) ? [] : ["local_server.py"];

  if (!(await requestOk(API_HEALTH_URL))) {
    appendLog("启动无 Docker 本地 API");
    localApiProcess = spawn(command, args, {
      cwd: backendCwd,
      shell: false,
      windowsHide: true,
      env: {
        ...process.env,
        APP_ENV: "local",
        DATABASE_URL: `sqlite:///${dbPath}`,
        COLD_CHAIN_DATA_DIR: dataDir,
        JWT_SECRET: "local-share-version",
        AMAP_KEY: envFile.AMAP_KEY || "",
        AMAP_SECURITY_CODE: envFile.AMAP_SECURITY_CODE || ""
      }
    });
    localApiProcess.stdout.on("data", (chunk) => appendLog(chunk.toString("utf8").trim()));
    localApiProcess.stderr.on("data", (chunk) => appendLog(chunk.toString("utf8").trim()));
  }

  await startStaticFrontend();
  await waitFor(API_HEALTH_URL, "本地后端服务", 30);
  await waitFor(FRONTEND_URL, "本地前端界面", 10);
  send("desktop-status", { state: "ready", message: "系统已在无 Docker 本地模式启动" });
  await reportDiagnostics();
  await mainWindow.loadURL(FRONTEND_URL);
}

function requestOk(url, timeoutMs = 2500) {
  return new Promise((resolve) => {
    const req = http.get(url, { timeout: timeoutMs }, (res) => {
      res.resume();
      resolve(res.statusCode >= 200 && res.statusCode < 400);
    });
    req.on("timeout", () => {
      req.destroy();
      resolve(false);
    });
    req.on("error", () => resolve(false));
  });
}

function requestJson(url, timeoutMs = 2500) {
  return new Promise((resolve) => {
    const req = http.get(url, { timeout: timeoutMs }, (res) => {
      let body = "";
      res.setEncoding("utf8");
      res.on("data", (chunk) => {
        body += chunk;
      });
      res.on("end", () => {
        if (res.statusCode >= 200 && res.statusCode < 400) {
          try {
            resolve(JSON.parse(body));
          } catch {
            resolve(null);
          }
        } else {
          resolve(null);
        }
      });
    });
    req.on("timeout", () => {
      req.destroy();
      resolve(null);
    });
    req.on("error", () => resolve(null));
  });
}

async function reportDiagnostics() {
  const info = await requestJson(API_DIAGNOSTICS_URL);
  if (!info) return;
  appendLog(`Database: ${info.database}; orders: ${info.order_count ?? "unknown"}; backups: ${info.backup_count ?? 0}`);
  appendLog(`Compose project: ${COMPOSE_PROJECT_NAME}; backup dir: ${info.backup_dir || "unknown"}`);
  send("desktop-status", {
    state: "ready",
    message: `系统已启动，订单 ${info.order_count ?? "?"} 单，备份 ${info.backup_count ?? 0} 个`
  });
}

async function waitFor(url, label, attempts = 60) {
  for (let index = 1; index <= attempts; index += 1) {
    if (await requestOk(url)) {
      appendLog(`${label} 已就绪`);
      return true;
    }
    send("desktop-status", {
      state: "booting",
      message: `正在等待 ${label} 就绪 (${index}/${attempts})`
    });
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
  throw new Error(`${label} 启动超时`);
}

async function ensureEnvFile() {
  const envFile = path.join(projectRoot, ".env");
  const envExample = path.join(projectRoot, ".env.example");
  if (!fs.existsSync(envFile) && fs.existsSync(envExample)) {
    fs.copyFileSync(envExample, envFile);
    appendLog("已从 .env.example 创建 .env");
  }
}

async function startServices() {
  if (booting) return;
  booting = true;
  try {
    send("desktop-status", { state: "booting", message: "正在检查 Docker" });
    await runCommand("docker", ["version", "--format", "{{.Server.Version}}"]);
    await ensureEnvFile();

    if ((await requestOk(API_HEALTH_URL)) && (await requestOk(FRONTEND_URL))) {
      appendLog("检测到本地服务已运行，直接进入系统");
      send("desktop-status", { state: "ready", message: "系统已启动" });
      await reportDiagnostics();
      await mainWindow.loadURL(FRONTEND_URL);
      return;
    }

    send("desktop-status", { state: "booting", message: "正在启动本地服务" });
    await runCommand("docker", ["compose", "-p", COMPOSE_PROJECT_NAME, "up", "-d", "--build"]);

    await waitFor(API_HEALTH_URL, "后端服务");
    await waitFor(FRONTEND_URL, "前端界面");

    send("desktop-status", { state: "ready", message: "系统已启动" });
    await reportDiagnostics();
    await mainWindow.loadURL(FRONTEND_URL);
  } catch (error) {
    appendLog(`Docker 启动不可用，尝试无 Docker 本地模式：${error instanceof Error ? error.message : String(error)}`);
    try {
      await startLocalServices();
    } catch (localError) {
      send("desktop-status", {
        state: "error",
        message: localError instanceof Error ? localError.message : String(localError)
      });
      appendLog(`启动失败：${localError instanceof Error ? localError.stack || localError.message : String(localError)}`);
    }
  } finally {
    booting = false;
  }
}

async function stopServices() {
  try {
    send("desktop-status", { state: "booting", message: "正在停止本地服务" });
    if (localApiProcess) {
      localApiProcess.kill();
      localApiProcess = null;
    }
    if (localFrontendServer) {
      localFrontendServer.close();
      localFrontendServer = null;
    }
    await runCommand("docker", ["compose", "-p", COMPOSE_PROJECT_NAME, "stop"]);
    send("desktop-status", { state: "idle", message: "服务已停止" });
  } catch (error) {
    send("desktop-status", {
      state: "error",
      message: error instanceof Error ? error.message : String(error)
    });
  }
}

function createMenu() {
  const template = [
    {
      label: "系统",
      submenu: [
        { label: "启动/进入系统", click: () => startServices() },
        { label: "打开状态页", click: () => mainWindow.loadFile(path.join(__dirname, "status.html")) },
        { label: "在浏览器中打开", click: () => shell.openExternal(FRONTEND_URL) },
        { type: "separator" },
        { label: "停止本地服务", click: () => stopServices() },
        { type: "separator" },
        { label: "退出", role: "quit" }
      ]
    },
    {
      label: "视图",
      submenu: [
        { label: "重新加载", role: "reload" },
        { label: "开发者工具", role: "toggleDevTools" },
        { type: "separator" },
        { label: "放大", role: "zoomIn" },
        { label: "缩小", role: "zoomOut" },
        { label: "实际大小", role: "resetZoom" }
      ]
    }
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1320,
    height: 860,
    minWidth: 1080,
    minHeight: 720,
    title: "生鲜物流协同优化系统",
    backgroundColor: "#0f172a",
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  createMenu();
  mainWindow.loadFile(path.join(__dirname, "status.html"));
  mainWindow.once("ready-to-show", () => startServices());
}

ipcMain.handle("desktop:start", () => startServices());
ipcMain.handle("desktop:stop", () => stopServices());
ipcMain.handle("desktop:open-external", () => shell.openExternal(FRONTEND_URL));
ipcMain.handle("desktop:project-root", () => projectRoot);

app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  if (localApiProcess) localApiProcess.kill();
  if (localFrontendServer) localFrontendServer.close();
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
