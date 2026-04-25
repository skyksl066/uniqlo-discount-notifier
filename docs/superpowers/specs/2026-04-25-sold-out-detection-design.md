# 已售罄商品檢測設計規格

**日期**: 2026-04-25  
**主題**: 檢測並通知已售罄商品  
**優先級**: 中等

---

## 背景

UNIQLO 商品頁面在售罄時會顯示「已售罄」標籤，當前應用無法檢測此狀態。需要支援：
1. 自動檢測售罄狀態
2. 分離已售罄商品，單獨發送 Slack 通知
3. 避免額外 HTTP 請求（現有單次請求中完成檢測）

---

## 功能需求

### 核心需求

1. **檢測售罄標籤**
   - HTML 結構：`<i class="archive icon"></i>` 存在即為售罄
   - 在單次 HTTP 請求中完成檢測（不增加額外請求）

2. **分離已售罄商品**
   - 檢測到售罄即提早返回，不解析價格圖表
   - 返回商品名稱和 URL（已售罄商品無價格數據）

3. **發送獨立通知**
   - 已售罄商品用單獨的 Slack 訊息通知
   - 保持現有的折扣商品訊息格式不變

4. **日誌記錄**
   - 售罄商品寫入日誌，便於追蹤

---

## 實現設計

### 資料結構

#### `get_product_data()` 返回值

```python
# 折扣商品
{
    'status': 'active',
    'name': '女 輕便羽絨外套',
    'url': 'https://...',
    'discount_rate': 0.50,
    'original_price': 2990.0,
    'current_price': 1490.0,
    'min_price': 1490.0
}

# 已售罄商品
{
    'status': 'sold_out',
    'name': '男 搖粒絨外套',
    'url': 'https://...'
}
```

**變更**:
- 新增 `status` 字段（'active' | 'sold_out'）
- 售罄商品只包含 status、name、url（無價格字段）

### 邏輯流程

#### `get_product_data(url)` 修改

```python
def get_product_data(url, session=None):
    # ... 既有的 HTTP 請求和初始化邏輯 ...
    soup = BeautifulSoup(html, 'html.parser')
    
    # 1. 檢測售罄狀態 (新增)
    if soup.find('i', class_='archive icon'):
        product_name = ...  # 取商品名稱（現有邏輯）
        return {
            'status': 'sold_out',
            'name': product_name,
            'url': url.strip()
        }
    
    # 2. 後續處理（現有邏輯保持不變）
    # - 取商品名稱
    # - 解析價格圖表
    # - 計算折扣率
    return {
        'status': 'active',
        'name': product_name,
        'url': url.strip(),
        ...
    }
```

#### `main()` 函數修改

```python
def main():
    # ... 既有邏輯 ...
    
    qualified_products = []      # 有折扣的商品
    sold_out_products = []       # 已售罄的商品
    
    for url in urls:
        product_data = get_product_data(url, session=scraper)
        if product_data:
            if product_data['status'] == 'sold_out':
                sold_out_products.append(product_data)
            else:
                qualified_products.append(product_data)
        time.sleep(1)
    
    # 1. 發送折扣商品通知（現有邏輯保持不變）
    # ...
    
    # 2. 發送售罄商品通知（新增）
    if sold_out_products:
        send_sold_out_notification(client, CHANNEL, sold_out_products)
```

### Slack 訊息格式

#### 折扣商品訊息（保持不變）
```
UNIQLO 關注商品：
Item：女 輕便羽絨外套
Url：https://...
Original Price: 2990
Current Price: 1490
Lowest Price: 1490
Discount Rate：50.17%
```

#### 售罄商品訊息（新增）
```
UNIQLO 商品已售罄通知：
• 女 輕便羽絨外套 — https://...
• 男 搖粒絨外套 — https://...
```

---

## 測試需求

### 單元測試

1. **售罄商品檢測**
   - 輸入: 含 `<i class="archive icon">` 的 HTML
   - 預期: 返回 `status='sold_out'`

2. **正常商品不受影響**
   - 輸入: 不含售罄標籤的 HTML
   - 預期: 返回 `status='active'` 及完整價格數據

3. **商品名稱提取**
   - 售罄商品應正確提取商品名稱
   - 支持 TocasUI v3 和 v4 結構

### 集成測試

1. 售罄和折扣商品混合時，能正確分離
2. 售罄商品訊息單獨發送
3. 折扣商品訊息格式不變

---

## 實現步驟

1. 修改 `get_product_data()` 新增售罄檢測邏輯
2. 修改 `main()` 分離已售罄商品
3. 新增 `send_sold_out_notification()` 函數
4. 新增單元測試用例
5. 驗證邏輯正確性

---

## 風險與考量

### 潛在風險

1. **售罄標籤結構變化**
   - 風險: goodjack.tw 改變 HTML 結構
   - 緩解: 添加後備檢測邏輯（如檢測「已售罄」文字）

2. **CloudFlare 限制**
   - 風險: 過多 request 被擋
   - 緩解: 單次 request 完成檢測，不增加額外請求

### 考量事項

1. **移除監控清單** — 暫不實施，後續再考慮
2. **售罄歷史追蹤** — 可在日誌中記錄，暫不存儲數據庫
3. **自動恢復上架** — 暫不支援，假設售罄後不再上架同樣商品

---

## 定義完成

✅ `get_product_data()` 返回 status 字段  
✅ 售罄商品單獨通知，折扣商品訊息不變  
✅ 單元測試覆蓋售罄/正常兩種情況  
✅ 驗證在 GitHub Actions 上運行無誤  
