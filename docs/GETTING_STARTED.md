# 生鲜冷链物流网站上手教程

这份教程用于让第一次打开仓库的人快速体验项目。若只是想看网页效果，优先使用“单页演示”；若需要调试前后端源码，再启动完整平台。

## 方式一：在线体验

如果仓库已经开启 GitHub Pages，直接访问：

```text
https://xiaozuo497.github.io/-/
```

页面会显示项目入口，点击“进入网页演示”即可打开生鲜冷链物流单页网站。

如果暂时打不开，说明 GitHub Pages 还没有开启。开启步骤：

1. 进入仓库页面，点击 `Settings`。
2. 左侧找到 `Pages`。
3. `Build and deployment` 选择 `Deploy from a branch`。
4. `Branch` 选择 `main`，目录选择 `/root`。
5. 保存后等待 1 到 3 分钟，再访问上面的在线地址。

## 方式二：本地直接打开

适合没有开发环境、只想快速体验的人。

1. 在 GitHub 页面点击绿色 `Code` 按钮。
2. 点击 `Download ZIP` 下载项目。
3. 解压 ZIP。
4. 双击打开：

```text
web-demo/生鲜物流1.0.html
```

这个单页演示可以直接在浏览器中运行，主要包含：

- 订单管理：录入配送订单，查看综合成本、里程、碳排放、货损率和准时率。
- 三维装箱：查看冷藏车箱体、周转箱摆放、空间利用率、装载率和装箱顺序。
- 路径优化与 QGIS：查看配送路线、车辆分配、预计抵达状态，并导出 QGIS 兼容点位文件。

## 地图功能说明

仓库中不会公开个人高德地图 Key。若需要使用真实地图和路径服务，请打开：

```text
web-demo/生鲜物流1.0.html
```

搜索并替换以下占位内容：

```javascript
const AMAP_KEY = '请填写你的高德地图 Key';
const AMAP_SECURITY_CODE = '请填写你的高德地图安全密钥';
```

如果不填写 Key，仍可体验订单、装箱、指标展示等核心流程，但部分地图能力可能无法正常加载。

## 方式三：启动完整前后端平台

适合想查看 Vue 前端、FastAPI 后端、数据库接口和 Electron 桌面端源码的人。

```powershell
cd cold-chain-platform
Copy-Item .env.example .env
docker compose up --build
```

启动后访问：

```text
前端：http://localhost:5173
后端接口文档：http://localhost:8000/docs
健康检查：http://localhost:8000/api/health
```

默认演示账号：

```text
管理员：admin / admin123
调度员：dispatcher / dispatch123
仓库员：warehouse / warehouse123
司机：driver / driver123
```

## 推荐体验顺序

1. 进入“订单管理”，添加或查看梨类配送订单。
2. 点击“运行并展示算法结果”，观察综合成本、总里程、碳排放、货损率与准时送达率。
3. 进入“三维装箱”，生成装箱方案，查看冷藏车内周转箱布局。
4. 进入“路径优化 & QGIS”，生成最优公路路径，并查看每辆车的配送顺序和履约状态。
5. 如需二次分析，导出 QGIS 点位文件。

## 常见问题

**为什么在线页面打不开？**

通常是 GitHub Pages 还没有开启，或刚开启还在部署中。请等待几分钟后刷新。

**为什么地图不显示？**

需要填写自己的高德地图 Key 和安全密钥。开源仓库不会提交私人 Key。

**只想看效果，需要安装 Docker 吗？**

不需要。打开 `web-demo/生鲜物流1.0.html` 即可体验单页演示。

