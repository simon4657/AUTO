# 自動交易系統 - Render 部署指南

本指南將引導您將自動交易系統部署到 Render 平台。系統包含一個 Flask 後端和一個整合的 HTML/CSS/JS 前端。

## 系統架構

- **後端**: Flask 應用程式，提供 API 端點用於參數管理和策略控制。
- **前端**: 整合在 Flask `static` 目錄中的單頁應用程式，提供用戶界面。
- **數據庫**: 使用 SQLite，數據庫文件將存儲在 Render 的持久化存儲中。

## 部署步驟

### 1. 準備您的 GitHub 倉庫

1.  **創建一個新的 GitHub 倉庫**。
2.  **將 `render_deployment` 目錄中的所有文件推送到您的倉庫**。確保包含以下文件：
    - `backend/` (包含所有後端代碼)
    - `render.yaml`

### 2. 在 Render 上創建新服務

1.  **登錄到您的 Render 帳戶**。
2.  點擊 **New +** > **Blueprint**。
3.  **連接您的 GitHub 帳戶** 並選擇您剛剛創建的倉庫。
4.  Render 將自動檢測 `render.yaml` 文件並配置服務。

### 3. 配置服務

- **服務名稱**: Render 將使用 `render.yaml` 中定義的名稱 (`auto-trading-system`)。
- **環境**: Python 環境將自動選擇。
- **構建命令**: `pip install -r requirements.txt`
- **啟動命令**: `python main.py`
- **環境變量**: `SECRET_KEY` 將自動生成。

### 4. 部署

點擊 **Create Blueprint**。Render 將開始構建和部署您的應用程式。部署完成後，您將獲得一個公開的 URL，例如 `https://auto-trading-system.onrender.com`。

## 使用部署的應用程式

- **訪問 URL**: 在瀏覽器中打開您的 Render URL。
- **管理參數**: 使用前端界面更新交易參數。
- **控制策略**: 啟動或停止交易策略。

## 健康檢查

Render 將使用 `/health` 端點來監控您的應用程式的健康狀況。如果應用程式不健康，Render 將自動重啟它。

## 持久化存儲

SQLite 數據庫文件 (`app.db`) 將存儲在 Render 的持久化存儲中，確保在重啟之間數據不會丟失。

## 故障排除

- **查看日誌**: 在 Render 儀表板中查看應用程式日誌以進行調試。
- **檢查環境變量**: 確保所有必要的環境變量都已正確設置。
- **本地測試**: 在本地運行應用程式以重現和解決問題。

## 結論

通過遵循本指南，您可以輕鬆地將自動交易系統部署到 Render 平台，並利用其自動擴展、健康檢查和持久化存儲等功能。

