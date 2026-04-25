# 已售罄商品檢測 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 檢測 UNIQLO 商品的已售罄狀態，並通過獨立的 Slack 訊息通知。

**Architecture:** 
在單次 HTTP 請求中檢測 `<i class="archive icon">` 標籤，判斷售罄狀態。修改 `get_product_data()` 返回結構加入 `status` 欄位，分離已售罄和折扣商品，分別發送不同格式的 Slack 訊息。

**Tech Stack:** 
BeautifulSoup4 (HTML 解析)、Slack SDK (訊息發送)、unittest (測試)

---

## Task 1: 寫測試 — 檢測已售罄商品

**Files:**
- Modify: `test_app.py`

- [ ] **Step 1: 在 test_app.py 末尾新增售罄商品測試**

在 `TestGetProductData` 類別最後新增此測試方法（在 `if __name__ == '__main__':` 之前）：

```python
    # ------------------------------------------------------------------ #
    #  Test 9: 已售罄商品
    # ------------------------------------------------------------------ #
    @patch('app.requests.get')
    def test_sold_out_product(self, mock_get):
        """檢測到已售罄標籤時應返回 status='sold_out'，不解析價格"""
        html = """<!DOCTYPE html>
<html lang="zh-TW">
<head><title>女 輕便羽絨外套 | UQ 搜尋</title></head>
<body>
<div class="nine wide large screen column">
  <h1 class="ts dividing big header">
    女 輕便羽絨外套
    <div class="sub header">UNIQLO 商品編號 u0000000053269</div>
  </h1>
</div>
<div class="sixteen wide column">
    <div class="ts basic fitted segment">
        <a class="ts horizontal basic circular label"><span style="color: #5A5A5A;"><i class="archive icon"></i>已售罄</span></a>
    </div>
</div>
<canvas id="priceChart"></canvas>
</body>
</html>"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        url = "https://uq.goodjack.tw/hmall-products/u0000000053269"
        result = get_product_data(url)

        self.assertIsNotNone(result, "應返回已售罄商品數據")
        self.assertEqual(result['status'], 'sold_out')
        self.assertEqual(result['name'], "女 輕便羽絨外套")
        self.assertEqual(result['url'], url)
        self.assertNotIn('discount_rate', result, "已售罄商品不應包含 discount_rate")
        logger.success(f"[PASS] test_sold_out_product — {result['name']} 狀態: {result['status']}")
```

- [ ] **Step 2: 執行測試確認會失敗**

```bash
python -m unittest test_app.TestGetProductData.test_sold_out_product -v
```

預期輸出：`FAIL` - `KeyError: 'status'` 或 `AssertionError: 'sold_out' != None`

- [ ] **Step 3: 提交測試**

```bash
git add test_app.py
git commit -m "test: add sold-out product detection test"
```

---

## Task 2: 實施 get_product_data() 售罄檢測邏輯

**Files:**
- Modify: `app.py:30-123` (get_product_data 函數)

- [ ] **Step 1: 修改 get_product_data() 新增售罄檢測**

找到 `app.py` 中 `def get_product_data(url, session=None):` 函數，將整個函數替換為：

```python
def get_product_data(url, session=None):
    """獲取產品數據或檢測已售罄狀態"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://uq.goodjack.tw/',
            'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }

        http_client = session if session is not None else cloudscraper.create_scraper()
        logger.info(f'Accessing: {url.strip()}')

        response = http_client.get(url.strip(), headers=headers, timeout=30)
        response.raise_for_status()

        html = response.text
        soup = BeautifulSoup(html, 'html.parser')

        # 獲取商品名稱
        # 支援 TocasUI v4 (ts-header) 與 v3 (ts dividing big header) 兩種結構
        h1 = (
            soup.find('h1', class_='ts-header')
            or soup.find('h1', class_='ts dividing big header')
        )
        if h1:
            # TocasUI v3：sub header 在 h1 內，需移除後再取文字
            sub_header = h1.find('div', class_='sub header')
            if sub_header:
                sub_header.decompose()
            product_name = h1.get_text().strip()
        else:
            # 最終回退：從 <title> 標籤解析商品名稱（格式：「商品名稱 | UQ 搜尋」）
            title_tag = soup.find('title')
            if title_tag and '|' in title_tag.get_text():
                product_name = title_tag.get_text().split('|')[0].strip()
            else:
                logger.debug(f'Page snippet: {html[:1000]}')
                logger.error(f'Could not find product name in URL: {url}')
                return None
        logger.info(f'Product: {product_name}')

        # 檢測是否已售罄（新增邏輯）
        if soup.find('i', class_='archive icon'):
            logger.warning(f'Product sold out: {product_name}')
            return {
                'status': 'sold_out',
                'name': product_name,
                'url': url.strip()
            }

        # 獲取價格數據 (從伺服器端渲染的 Chart.js 初始化腳本中提取)
        script_tag = soup.find('script', string=re.compile(r"label:\s*'價格'"))
        if not script_tag:
            logger.error(f'Could not find price chart script in URL: {url}')
            return None

        price_data_match = re.search(
            r"label:\s*'價格',\s*data:\s*(\[.*?\]),\s*backgroundColor",
            script_tag.string, re.DOTALL
        )
        if not price_data_match:
            logger.error(f'Could not find price chart data in URL: {url}')
            return None

        price_data = json.loads(price_data_match.group(1))
        prices = [float(data['y']) for data in price_data]

        if not prices:
            logger.error(f'Empty price data for URL: {url}')
            return None

        # 計算價格信息
        max_price = max(prices)
        min_price = min(prices)
        current_price = prices[-1]
        discount_rate = (max_price - current_price) / max_price if max_price > 0 else 0

        logger.info(f'Price stats - Max: {max_price}, Min: {min_price}, Current: {current_price}, Discount: {discount_rate:.2%}')

        return {
            'status': 'active',
            'name': product_name,
            'url': url.strip(),
            'discount_rate': discount_rate,
            'original_price': max_price,
            'current_price': current_price,
            'min_price': min_price
        }

    except Exception as e:
        logger.error(f"Error processing URL {url}: {e}")
        return None
```

- [ ] **Step 2: 執行測試確認通過**

```bash
python -m unittest test_app.TestGetProductData.test_sold_out_product -v
```

預期輸出：`OK`

- [ ] **Step 3: 確認既有測試仍通過**

```bash
python -m unittest test_app.TestGetProductData.test_discounted_product -v
python -m unittest test_app.TestGetProductData.test_full_price_product -v
```

預期輸出：兩個測試都 `OK`

- [ ] **Step 4: 提交修改**

```bash
git add app.py
git commit -m "feat: add sold-out product detection in get_product_data()"
```

---

## Task 3: 寫測試 — TocasUI v4 售罄商品

**Files:**
- Modify: `test_app.py`

- [ ] **Step 1: 在測試類別新增 v4 售罄商品測試**

在 Task 1 新增的測試之後新增：

```python
    # ------------------------------------------------------------------ #
    #  Test 10: TocasUI v4 已售罄商品
    # ------------------------------------------------------------------ #
    @patch('app.requests.get')
    def test_sold_out_product_v4(self, mock_get):
        """TocasUI v4 結構的已售罄商品也應正確檢測"""
        html = """<!DOCTYPE html>
<html lang="zh-TW">
<head><title>男 搖粒絨外套 | UQ 搜尋</title></head>
<body>
<div class="ts-container">
  <h1 class="ts-header is-big is-dividing">
    男 搖粒絨外套
  </h1>
</div>
<div class="sixteen wide column">
    <div class="ts basic fitted segment">
        <a class="ts horizontal basic circular label"><span style="color: #5A5A5A;"><i class="archive icon"></i>已售罄</span></a>
    </div>
</div>
<canvas id="priceChart"></canvas>
</body>
</html>"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        url = "https://uq.goodjack.tw/hmall-products/u0000000052992"
        result = get_product_data(url)

        self.assertIsNotNone(result)
        self.assertEqual(result['status'], 'sold_out')
        self.assertEqual(result['name'], "男 搖粒絨外套")
        logger.success(f"[PASS] test_sold_out_product_v4 — {result['name']} v4 結構檢測成功")
```

- [ ] **Step 2: 執行測試確認通過**

```bash
python -m unittest test_app.TestGetProductData.test_sold_out_product_v4 -v
```

預期輸出：`OK`

- [ ] **Step 3: 提交**

```bash
git add test_app.py
git commit -m "test: add TocasUI v4 sold-out product test"
```

---

## Task 4: 新增 send_sold_out_notification() 函數

**Files:**
- Modify: `app.py:21-27` (在 post_message 函數後新增)

- [ ] **Step 1: 在 app.py 的 post_message() 函數後新增 send_sold_out_notification()**

找到 `def post_message(client, channel, text):` 函數（約第 21 行），在其後添加新函數：

```python

def send_sold_out_notification(client, channel, sold_out_products):
    """發送已售罄商品通知"""
    if not sold_out_products:
        return
    
    items = '\n'.join(
        f"• {product['name']} — {product['url']}"
        for product in sold_out_products
    )
    
    text = f"""UNIQLO 商品已售罄通知：
{items}"""
    
    post_message(client, channel, text)
    logger.info(f"Sent sold-out notification for {len(sold_out_products)} products")
```

- [ ] **Step 2: 驗證語法正確**

```bash
python -m py_compile app.py
```

預期輸出：無錯誤

- [ ] **Step 3: 提交**

```bash
git add app.py
git commit -m "feat: add send_sold_out_notification function"
```

---

## Task 5: 修改 main() 函數分離已售罄商品

**Files:**
- Modify: `app.py:126-177` (main 函數)

- [ ] **Step 1: 修改 main() 函數內部邏輯**

找到 `def main():` 函數，將其替換為：

```python
def main():
    TOKEN = os.environ["SLACK_TOKEN"]
    CHANNEL = os.environ["SLACK_CHANNEL"]
    if not TOKEN or not CHANNEL:
        logger.error("environment variable not set")
        sys.exit(1)

    # 初始化 Slack 客戶端
    client = WebClient(token=TOKEN)

    # 從文件讀取產品列表
    try:
        with open('data/product_list.txt', 'r') as file:
            urls = file.readlines()
        logger.info(f'Loaded {len(urls)} products from file')
    except FileNotFoundError:
        logger.error("Product list file not found at data/product_list.txt")
        sys.exit(1)

    qualified_products = []
    sold_out_products = []

    # 使用 cloudscraper 繞過 CloudFlare 挑戰
    scraper = cloudscraper.create_scraper()

    # 處理每個產品 URL
    for url in urls:
        if not url.strip():
            continue

        product_data = get_product_data(url, session=scraper)
        if product_data:
            if product_data['status'] == 'sold_out':
                sold_out_products.append(product_data)
            else:
                qualified_products.append(product_data)
        time.sleep(1)

    # 發送已售罄商品通知
    if sold_out_products:
        send_sold_out_notification(client, CHANNEL, sold_out_products)

    # 每個消息包含的產品數量
    unit_size = 3
    # 計算需要發送的消息數量
    num_units = (len(qualified_products) + unit_size - 1) // unit_size

    for i in range(num_units):
        start_index = i * unit_size
        end_index = min((i + 1) * unit_size, len(qualified_products))
        unit_products = qualified_products[start_index:end_index]

        message = "UNIQLO 關注商品：\n"
        for product in unit_products:
            message += f"\nItem：{product['name']}\nUrl：{product['url']}\nOriginal Price: {product['original_price']}\nCurrent Price: {product['current_price']}\nLowest Price: {product['min_price']}\nDiscount Rate：{product['discount_rate']:.2%}\n"

        # 發送通知到 Slack
        logger.info('Sending Slack message')
        post_message(client, CHANNEL, message)
```

- [ ] **Step 2: 驗證語法**

```bash
python -m py_compile app.py
```

預期輸出：無錯誤

- [ ] **Step 3: 提交**

```bash
git add app.py
git commit -m "feat: separate sold-out and discounted products in main()"
```

---

## Task 6: 寫整合測試 — 混合場景

**Files:**
- Modify: `test_app.py`

- [ ] **Step 1: 在測試類別新增混合商品測試**

在最後一個測試之後新增：

```python
    # ------------------------------------------------------------------ #
    #  Test 11: 混合商品場景（折扣 + 售罄）
    # ------------------------------------------------------------------ #
    def test_mixed_products(self):
        """驗證可以正確區分折扣商品和售罄商品"""
        # 建立兩個不同的 mock 響應
        price_rows_discount = [
            ("2025-01-01", 2990),
            ("2025-03-01", 1990),
        ]
        html_discount = _make_product_html("女", "輕便羽絨外套", "u0000000053269", price_rows_discount)
        
        html_sold_out = """<!DOCTYPE html>
<html lang="zh-TW">
<head><title>男 搖粒絨外套 | UQ 搜尋</title></head>
<body>
<h1 class="ts dividing big header">
    男 搖粒絨外套
    <div class="sub header">UNIQLO 商品編號 u0000000052992</div>
</h1>
<div class="sixteen wide column">
    <div class="ts basic fitted segment">
        <a class="ts horizontal basic circular label"><span style="color: #5A5A5A;"><i class="archive icon"></i>已售罄</span></a>
    </div>
</div>
</body>
</html>"""

        with patch('app.requests.get') as mock_get:
            # 第一次調用：折扣商品
            mock_resp_1 = MagicMock()
            mock_resp_1.status_code = 200
            mock_resp_1.text = html_discount
            mock_resp_1.raise_for_status = MagicMock()
            
            # 第二次調用：售罄商品
            mock_resp_2 = MagicMock()
            mock_resp_2.status_code = 200
            mock_resp_2.text = html_sold_out
            mock_resp_2.raise_for_status = MagicMock()
            
            mock_get.side_effect = [mock_resp_1, mock_resp_2]
            
            url_discount = "https://uq.goodjack.tw/hmall-products/u0000000053269"
            url_sold_out = "https://uq.goodjack.tw/hmall-products/u0000000052992"
            
            result_discount = get_product_data(url_discount)
            result_sold_out = get_product_data(url_sold_out)
            
            # 驗證折扣商品
            self.assertIsNotNone(result_discount)
            self.assertEqual(result_discount['status'], 'active')
            self.assertIn('discount_rate', result_discount)
            
            # 驗證售罄商品
            self.assertIsNotNone(result_sold_out)
            self.assertEqual(result_sold_out['status'], 'sold_out')
            self.assertNotIn('discount_rate', result_sold_out)
            
            logger.success("[PASS] test_mixed_products — 折扣和售罄商品分類正確")
```

- [ ] **Step 2: 執行測試確認通過**

```bash
python -m unittest test_app.TestGetProductData.test_mixed_products -v
```

預期輸出：`OK`

- [ ] **Step 3: 提交**

```bash
git add test_app.py
git commit -m "test: add mixed products scenario test"
```

---

## Task 7: 驗證所有測試並最終提交

**Files:**
- `test_app.py`, `app.py`

- [ ] **Step 1: 執行所有測試確認通過**

```bash
python -m unittest test_app.TestGetProductData -v
```

預期輸出：所有測試都 `OK` (共 11 個測試)

- [ ] **Step 2: 檢查是否有任何錯誤日誌**

檢查上一步的輸出，確認沒有 `FAIL` 或 `ERROR`

- [ ] **Step 3: 驗證代碼風格**

```bash
python -m py_compile app.py test_app.py
```

預期輸出：無錯誤

- [ ] **Step 4: 查看最近的提交日誌**

```bash
git log --oneline -5
```

預期輸出應包含本次的幾個 commit

- [ ] **Step 5: 最終確認功能**

運行完整測試：

```bash
python -m unittest test_app -v 2>&1 | tee test_results.txt
```

檢查輸出確認：
- test_sold_out_product 通過
- test_sold_out_product_v4 通過
- test_mixed_products 通過
- 所有既有測試仍通過

---

## 驗證完成標準

✅ `get_product_data()` 返回 `status` 欄位（'active' 或 'sold_out'）  
✅ 售罄商品檢測邏輯正確（HTML 中含 `<i class="archive icon">`）  
✅ 已售罄商品未解析價格圖表（提早返回）  
✅ `send_sold_out_notification()` 函數正常運作  
✅ `main()` 函數正確分離已售罄和折扣商品  
✅ 所有 11 個單元測試通過  
✅ TocasUI v3 和 v4 結構都支援  
✅ 代碼無語法錯誤
