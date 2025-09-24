# 台灣股票交易系統

## 系統概述

這是一個專業的台灣股票交易系統，具備實時數據獲取、多策略交易和完整的台股交易時間管理功能。

## 主要功能

### ✅ 修復完成的功能
- **Yahoo Finance數據獲取**：穩定獲取台股實時數據
- **台灣股市交易時間管理**：完整的交易時間邏輯
- **TYPE1黃柱策略**：基於Pine Script的專業交易策略
- **多策略支援**：TYPE1-TYPE4不同交易策略
- **專業交易介面**：仿真專業交易軟體風格

### 🔧 技術特色
- Flask後端架構
- Yahoo Finance API整合
- Pine Script技術指標計算
- 台股交易時間自動管理
- 響應式前端介面

## 快速部署

### Render平台部署

1. **Fork此專案到您的GitHub**
2. **在Render Dashboard中：**
   - 選擇 "New Web Service"
   - 連接您的GitHub repository
   - 使用以下設定：
     - **Build Command:** `pip install -r requirements.txt`
     - **Start Command:** `python main.py`
     - **Python Version:** 3.11.0

3. **環境變數設定（可選）：**
   ```bash
   SECRET_KEY=your-secret-key-here
   FLASK_DEBUG=False
   ```

### 本地開發

```bash
# 1. 克隆專案
git clone <your-repo-url>
cd taiwan_stock_system_clean

# 2. 創建虛擬環境
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 3. 安裝依賴
pip install -r requirements.txt

# 4. 啟動應用
python main.py
```

## 系統架構

```
taiwan_stock_system_clean/
├── main.py                          # Flask主應用
├── requirements.txt                 # 依賴包列表
├── runtime.txt                      # Python版本
├── render.yaml                      # Render部署配置
├── services/
│   ├── yahoo_finance_fixed.py       # 修復後的Yahoo Finance服務
│   ├── trading_time_manager.py      # 交易時間管理器
│   └── strategy_engine_new.py       # 策略引擎
├── routes/
│   └── strategy_new.py              # 策略路由
├── static/
│   └── index.html                   # 前端介面
└── models/                          # 數據模型
```

## API端點

### 策略管理
- `POST /api/strategy/start` - 啟動策略
- `POST /api/strategy/stop` - 停止策略
- `GET /api/strategy/status` - 獲取策略狀態
- `POST /api/strategy/scan` - 手動掃描股票

### 交易時間
- `GET /api/strategy/trading-time` - 獲取交易時間狀態

### 系統狀態
- `GET /health` - 健康檢查

## 交易時間規則

### 台股交易時間
- **上午交易：** 09:00 - 12:00
- **午休時間：** 12:00 - 13:30
- **下午收盤：** 13:30
- **盤前準備：** 08:30 - 09:00
- **盤後時間：** 13:30 - 14:30

### 策略運行規則
- **TYPE1 黃柱策略：** 可在盤前、交易時間、盤後運行
- **TYPE2-4 其他策略：** 僅在交易時間運行

## 使用說明

### 1. 訪問系統
部署完成後，訪問您的Render URL即可使用系統。

### 2. 策略操作
1. 選擇策略類型（TYPE1-TYPE4）
2. 設定交易參數
3. 點擊"啟動策略"開始運行

### 3. 監控功能
- 實時查看策略狀態
- 監控交易時間
- 查看掃描結果

## 技術支援

### 常見問題

**Q: Yahoo Finance連接失敗怎麼辦？**
A: 系統會自動使用備用數據，確保正常運行。

**Q: 策略無法啟動？**
A: 檢查當前是否為交易時間，TYPE1策略可全天運行。

**Q: 如何查看系統日誌？**
A: 在Render Dashboard的Logs標籤中查看。

### 版本資訊
- **版本：** v2.0 (修復版)
- **修復日期：** 2025年9月23日
- **主要修復：** Yahoo Finance數據獲取、交易時間管理

## 授權

本專案僅供學習和研究使用。

---

**注意：** 本系統為模擬交易系統，不提供實際交易功能。投資有風險，請謹慎決策。
