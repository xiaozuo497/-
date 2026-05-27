# 生鲜梨冷链三维装箱与路径优化协同系统

本仓库开源一个面向生鲜梨冷链配送场景的协同优化系统，覆盖订单管理、四箱型周转箱、三维装箱、车辆路径、货损预测、碳排放核算和司机执行闭环。

系统方法以 `MLP 货损预测 + GA-2-opt 路径优化 + 三维装箱可行性检验 + CarbonCost 绿色物流核算` 为统一口径。它不是单独追求最短路径，而是在车辆载重、货厢空间、顶部通风、支撑率、卸货顺序、准时率和货损风险都可控的前提下，选择综合成本更低的配送方案。

## 仓库内容

```text
web-demo/
  生鲜物流1.0.html                 单文件网页演示，可直接用浏览器打开

cold-chain-platform/
  backend/                         FastAPI 后端、优化服务、数据库模型和测试
  frontend/                        Vue 3 前端管理台和司机端页面
  desktop/                         Electron 桌面启动器源码
  infra/                           PostgreSQL 初始化和部署相关文件
  docs/                            项目说明、算法说明和展示材料
  tools/                           报告生成、Docker 检查等辅助脚本

docs/
  algorithm/OPEN_SOURCE_ALGORITHM.md   GitHub 开源版算法逻辑说明
  design/                              软件需求、系统架构与数据库设计文档
```

## 算法口径

- 箱型：`LH-600-140`、`LH-600-220`、`LH-600-300`、`LH-600-340`。
- 货损：MLP 输出 `PredLoss_i`，并进入货损成本 `C_loss`。
- 路径：GA 生成客户访问序列，2-opt 做局部改进。
- 装箱：600 x 400 mm 网格蛇形填充，输出 R/C/H 坐标。
- 可行性：AABB 碰撞检测、支撑率、顶部通风、载重、容积和卸货顺序校验。
- 履约：`OnTimeRate >= 95%`，强制时间窗站点不得迟到。
- 低碳：行驶排放和制冷/开门补偿能耗统一折算为 `CarbonCost`。

完整算法说明见 [docs/algorithm/OPEN_SOURCE_ALGORITHM.md](docs/algorithm/OPEN_SOURCE_ALGORITHM.md)。

## 快速开始

### 单页演示

直接打开：

```text
web-demo/生鲜物流1.0.html
```

### 平台源码

进入平台目录：

```powershell
cd cold-chain-platform
Copy-Item .env.example .env
docker compose up --build
```

访问：

```text
前端：http://localhost:5173
后端：http://localhost:8000/docs
健康检查：http://localhost:8000/api/health
```

默认演示账号：

```text
管理员：admin / admin123
调度员：dispatcher / dispatch123
仓库员：warehouse / warehouse123
司机：driver / driver123
```

## 说明

本仓库只开源源码、文档和演示页面，不包含 Windows 安装包、压缩包、`node_modules`、构建产物、本地数据库、备份数据和私有 `.env` 文件。
