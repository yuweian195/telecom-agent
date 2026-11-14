# NOC Wallboard

TelecomAgent 的 TypeScript + React 19 值班大屏，读取 FastAPI 最新分析结果。

## 开发

```bash
npm install
npm run dev
```

打开 `http://127.0.0.1:5173/wallboard/`，开发模式默认请求 `http://127.0.0.1:8000`。

可通过环境变量覆盖 API 地址：

```bash
VITE_API_BASE=http://127.0.0.1:8000 npm run dev
```

## 构建

```bash
npm run build
```

产物在 `dist/`。FastAPI 启动时会自动挂载到 `/wallboard/`：

```bash
cd ..
uvicorn app.main:app --reload
# http://127.0.0.1:8000/wallboard/
```

## 技术栈

- Vite 6
- React 19
- TypeScript 5
- 原生 CSS（无 UI 框架）
