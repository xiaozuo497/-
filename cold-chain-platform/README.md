# 生鲜梨冷链三维装箱与路径优化协同系统

本项目面向生鲜梨城市冷链配送场景，将订单管理、车辆调度、四箱型周转箱、三维装箱、路径优化、货损预测和绿色物流核算整合到同一套系统中。

算法口径以《生鲜梨冷链四箱型三维装箱与路径优化一体化模型方案》为准：

- 箱型：LH-600-140、LH-600-220、LH-600-300、LH-600-340。
- 货损：MLP 预测货损率 `PredLoss_i`，并进入综合成本 `C_loss`。
- 路径：遗传算法 GA 生成客户访问序列，2-opt 做局部改进。
- 装箱：600 x 400 mm 网格蛇形填充，输出 R/C/H 坐标，并做 AABB 碰撞、顶部通风、支撑率和卸货顺序校验。
- 绿色物流：行驶排放、制冷/开门补偿能耗统一折算为 `CarbonCost`。
- 履约约束：`OnTimeRate >= 95%`，强制时间窗站点不得迟到。

## 技术栈

- 后端：FastAPI、SQLAlchemy、PostgreSQL/SQLite、Python 启发式优化服务。
- 前端：Vue 3、TypeScript、Element Plus、Three.js。
- 桌面端：Electron，用于 Windows 本地启动和分享。
- 展示页：`生鲜物流1.0.html`，可单文件演示订单、装箱、路径和 QGIS 导出。

## 目录结构

```text
cold-chain-platform/
  backend/        FastAPI 后端与优化服务
  frontend/       Vue 管理后台和司机端 H5
  desktop/        Electron 桌面启动器
  docs/           算法、部署和项目展示材料
```

## 本地启动

复制环境变量：

```powershell
Copy-Item .env.example .env
```

使用 Docker Compose 启动数据库、后端和前端：

```powershell
docker compose up --build
```

访问地址：

```text
前端：http://localhost:5173
后端：http://localhost:8000/docs
健康检查：http://localhost:8000/api/health
```

## 当前实现

- 订单、车辆、四箱型基础数据。
- 路径优化与三维装箱耦合校验。
- 车辆载重、容积、箱数、时间窗和装箱可行性校验。
- R/C/H 装箱坐标输出与前端三维可视化。
- 碳排放、预测货损率、综合成本和准时率指标展示。
- 算法说明见 [docs/路径优化与三维装箱耦合算法说明.md](docs/路径优化与三维装箱耦合算法说明.md)。

## 开源说明

本仓库适合作为生鲜冷链物流、三维装箱、路径优化和绿色物流课程/竞赛/原型系统的参考实现。完整算法逻辑可直接放入 GitHub 项目主页或论文/说明文档，见仓库根目录的 `OPEN_SOURCE_ALGORITHM.md`。
