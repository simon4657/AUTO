# GitHub 和 Render 部署指南

## 📋 部署前準備

### 1. 檢查文件結構
確保您的項目目錄包含以下文件：
```
render_clean_final/
├── .gitignore          # Git忽略文件
├── main.py            # Flask主應用
├── requirements.txt   # Python依賴
├── runtime.txt        # Python版本
├── render.yaml        # Render配置
├── README.md          # 項目說明
├── DEPLOYMENT.md      # 部署指南
├── models/            # 數據模型
├── routes/            # API路由
├── services/          # 業務邏輯
├── static/            # 靜態文件
└── database/          # 數據庫文件
```

### 2. 重要提醒
- ✅ **已包含 .gitignore**: 自動忽略 venv、__pycache__ 等文件
- ✅ **移除 venv 資料夾**: 虛擬環境不應上傳到 GitHub
- ✅ **保留 requirements.txt**: Render 會自動安裝依賴

## 🚀 GitHub 上傳步驟

### 1. 初始化 Git 倉庫
```bash
cd render_clean_final
git init
```

### 2. 添加文件到 Git
```bash
git add .
git commit -m "Initial commit: Professional Trading System v1.0"
```

### 3. 連接 GitHub 倉庫
```bash
# 替換為您的 GitHub 倉庫地址
git remote add origin https://github.com/yourusername/trading-system-pro.git
git branch -M main
git push -u origin main
```

## 🌐 Render 部署步驟

### 1. 創建 Web Service
1. 登入 [Render Dashboard](https://dashboard.render.com)
2. 點擊 "New +" → "Web Service"
3. 選擇 "Build and deploy from a Git repository"
4. 連接您的 GitHub 帳號
5. 選擇剛才創建的倉庫

### 2. 配置部署設置
- **Name**: `trading-system-professional`
- **Environment**: `Python 3`
- **Region**: 選擇最近的區域
- **Branch**: `main`
- **Root Directory**: 留空（使用根目錄）
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python main.py`

### 3. 環境變量設置
在 "Environment" 標籤中添加：
```
FLASK_ENV=production
DATABASE_URL=sqlite:///database/app.db
PORT=8000
```

### 4. 高級設置
- **Auto-Deploy**: 啟用（代碼更新時自動部署）
- **Health Check Path**: `/api/strategy/status`

## 🔧 本地測試

在上傳到 GitHub 前，建議先本地測試：

```bash
# 創建新的虛擬環境
python3 -m venv venv
source venv/bin/activate

# 安裝依賴
pip install -r requirements.txt

# 啟動應用
python main.py
```

訪問 `http://localhost:8000` 確認系統正常運行。

## 📝 部署後驗證

部署成功後，您將獲得類似以下的 URL：
`https://trading-system-professional.onrender.com`

### 驗證步驟
1. 訪問主頁面，確認介面正常顯示
2. 測試策略選擇功能
3. 測試交易參數設定
4. 確認帳戶資訊即時更新
5. 驗證交易記錄功能

## ⚠️ 常見問題解決

### 問題1：部署失敗
**解決方案**：
- 檢查 requirements.txt 是否包含所有依賴
- 確認 Python 版本在 runtime.txt 中正確設置
- 查看 Render 部署日誌找出具體錯誤

### 問題2：應用無法啟動
**解決方案**：
- 確認 main.py 中的端口設置為 `0.0.0.0`
- 檢查環境變量是否正確設置
- 確認數據庫文件路徑正確

### 問題3：靜態文件無法載入
**解決方案**：
- 確認 static 資料夾結構正確
- 檢查 Flask 靜態文件配置
- 驗證文件路徑大小寫

## 🔄 更新部署

當您需要更新系統時：

```bash
# 修改代碼後
git add .
git commit -m "Update: description of changes"
git push origin main
```

Render 會自動檢測到更改並重新部署。

## 📞 技術支援

如遇到部署問題：
1. 檢查 Render 部署日誌
2. 確認所有文件都已正確上傳到 GitHub
3. 驗證環境變量設置
4. 測試本地環境是否正常

---

**部署成功後，您將擁有一個專業的台股自動交易系統！** 🎉

