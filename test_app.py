# -*- coding: utf-8 -*-
"""
Integration test for app.py get_product_data()
Uses mock HTTP responses that match the real uq.goodjack.tw HTML structure
so the parsing logic can be fully exercised without network access.
"""

import sys
import unittest
from unittest.mock import patch, MagicMock
from loguru import logger

# Patch loguru to also write to stdout so pytest/CI captures it
logger.remove()
logger.add(sys.stdout, level="DEBUG", colorize=False,
           format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {name}:{function}:{line} - {message}")

from app import get_product_data


def _make_product_html(product_sex, product_name, product_code, price_rows):
    """Build a minimal HTML page that matches the real goodjack.tw structure (TocasUI v3)."""
    price_json = ", ".join(
        f'{{"t":"{row[0]}","y":{row[1]}}}'
        for row in price_rows
    )
    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head><title>{product_sex} {product_name} | UQ 搜尋</title></head>
<body>
<div class="nine wide large screen column">
  <h1 class="ts dividing big header">
    {product_sex} {product_name}
    <div class="sub header">
      UNIQLO 商品編號 {product_code}
    </div>
  </h1>
</div>
<canvas id="priceChart"></canvas>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/2.9.4/Chart.bundle.min.js"
    integrity="sha256-xxx" crossorigin="anonymous"></script>
<script>
    let ctx = document.getElementById("priceChart");
    let pointBackgroundColor = [];
    let pointRadius = [];
    let priceChart = new Chart(ctx, {{
        type: 'LineWithLine',
        data: {{
            datasets: [{{
                label: '價格',
                data: [{price_json}],
                backgroundColor: 'rgba(255, 255, 255, 0)',
                borderColor: 'rgba(206, 94, 87, 1.0)',
                borderWidth: 2,
            }}]
        }}
    }});
</script>
</body>
</html>"""


def _make_product_html_v4(product_sex, product_name, product_code, price_rows):
    """Build a minimal HTML page that matches the goodjack.tw TocasUI v4 structure."""
    price_json = ", ".join(
        f'{{"t":"{row[0]}","y":{row[1]}}}'
        for row in price_rows
    )
    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head><title>{product_sex} {product_name} | UQ 搜尋</title></head>
<body>
<div class="ts-container">
  <h1 class="ts-header is-big is-dividing">
    {product_sex} {product_name}
  </h1>
  <div class="ts-text is-secondary">UNIQLO 商品編號 {product_code}</div>
</div>
<canvas id="priceChart"></canvas>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/2.9.4/Chart.bundle.min.js"
    integrity="sha256-xxx" crossorigin="anonymous"></script>
<script>
    let ctx = document.getElementById("priceChart");
    let pointBackgroundColor = [];
    let pointRadius = [];
    let priceChart = new Chart(ctx, {{
        type: 'LineWithLine',
        data: {{
            datasets: [{{
                label: '價格',
                data: [{price_json}],
                backgroundColor: 'rgba(255, 255, 255, 0)',
                borderColor: 'rgba(206, 94, 87, 1.0)',
                borderWidth: 2,
            }}]
        }}
    }});
</script>
</body>
</html>"""


class TestGetProductData(unittest.TestCase):

    def _mock_response(self, html):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    # ------------------------------------------------------------------ #
    #  Test 1: 正常商品（有折扣）
    # ------------------------------------------------------------------ #
    @patch('cloudscraper.create_scraper')
    def test_discounted_product(self, mock_create_scraper):
        """商品目前打折：折扣率應正確計算"""
        price_rows = [
            ("2024-09-01", 2990),
            ("2024-10-01", 2990),
            ("2024-11-15", 2990),
            ("2024-12-06", 1990),
            ("2025-01-10", 1990),
            ("2025-04-01", 1490),
        ]
        html = _make_product_html("女", "輕便羽絨外套", "u0000000053269", price_rows)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp
        mock_create_scraper.return_value = mock_session

        url = "https://uq.goodjack.tw/hmall-products/u0000000053269"
        result = get_product_data(url)

        self.assertIsNotNone(result, "should return product data, not None")
        self.assertEqual(result['name'], "女 輕便羽絨外套")
        self.assertEqual(result['url'], url)
        self.assertEqual(result['original_price'], 2990.0)
        self.assertEqual(result['current_price'], 1490.0)
        self.assertEqual(result['min_price'], 1490.0)
        expected_discount = (2990 - 1490) / 2990
        self.assertAlmostEqual(result['discount_rate'], expected_discount, places=4)
        self.assertEqual(result['status'], 'active')
        logger.success(f"[PASS] test_discounted_product — {result['name']} 折扣率 {result['discount_rate']:.2%}")

    # ------------------------------------------------------------------ #
    #  Test 2: 商品全價（無折扣）
    # ------------------------------------------------------------------ #
    @patch('cloudscraper.create_scraper')
    def test_full_price_product(self, mock_create_scraper):
        """商品維持原價：折扣率應為 0%"""
        price_rows = [
            ("2025-01-01", 1990),
            ("2025-02-01", 1990),
            ("2025-03-01", 1990),
        ]
        html = _make_product_html("男", "圓領T恤", "u0000000051098", price_rows)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp
        mock_create_scraper.return_value = mock_session

        url = "https://uq.goodjack.tw/hmall-products/u0000000051098"
        result = get_product_data(url)

        self.assertIsNotNone(result)
        self.assertEqual(result['name'], "男 圓領T恤")
        self.assertEqual(result['original_price'], 1990.0)
        self.assertEqual(result['current_price'], 1990.0)
        self.assertAlmostEqual(result['discount_rate'], 0.0, places=4)
        self.assertEqual(result['status'], 'active')
        logger.success(f"[PASS] test_full_price_product — {result['name']} 折扣率 {result['discount_rate']:.2%}")

    # ------------------------------------------------------------------ #
    #  Test 3: 多次價格變動
    # ------------------------------------------------------------------ #
    @patch('cloudscraper.create_scraper')
    def test_multiple_price_changes(self, mock_create_scraper):
        """多次降價：min_price 應為歷史最低，current_price 為最後一筆"""
        price_rows = [
            ("2024-09-01", 3990),
            ("2024-10-01", 2990),
            ("2024-11-01", 1990),
            ("2024-12-01", 2490),
            ("2025-01-01", 1490),
        ]
        html = _make_product_html("男", "羊毛混紡大衣", "u0000000050617", price_rows)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp
        mock_create_scraper.return_value = mock_session

        url = "https://uq.goodjack.tw/hmall-products/u0000000050617"
        result = get_product_data(url)

        self.assertIsNotNone(result)
        self.assertEqual(result['original_price'], 3990.0)
        self.assertEqual(result['min_price'], 1490.0)
        self.assertEqual(result['current_price'], 1490.0)
        self.assertEqual(result['status'], 'active')
        logger.success(f"[PASS] test_multiple_price_changes — {result['name']} 最高:{result['original_price']} 最低:{result['min_price']} 現在:{result['current_price']}")

    # ------------------------------------------------------------------ #
    #  Test 4: HTTP 錯誤（404）
    # ------------------------------------------------------------------ #
    @patch('cloudscraper.create_scraper')
    def test_http_error(self, mock_create_scraper):
        """HTTP 404 應回傳 None 且不拋出例外"""
        import requests as req
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req.exceptions.HTTPError("404 Not Found")
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp
        mock_create_scraper.return_value = mock_session

        url = "https://uq.goodjack.tw/hmall-products/u0000000099999"
        result = get_product_data(url)

        self.assertIsNone(result, "should return None on HTTP error")
        logger.success("[PASS] test_http_error — HTTP 404 正確回傳 None")

    # ------------------------------------------------------------------ #
    #  Test 5: HTML 結構遺漏商品名稱
    # ------------------------------------------------------------------ #
    @patch('cloudscraper.create_scraper')
    def test_missing_product_name(self, mock_create_scraper):
        """找不到商品名稱 h1 標籤時應回傳 None"""
        html = "<html><body><p>No product here</p></body></html>"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp
        mock_create_scraper.return_value = mock_session

        url = "https://uq.goodjack.tw/hmall-products/u0000000050586"
        result = get_product_data(url)

        self.assertIsNone(result)
        logger.success("[PASS] test_missing_product_name — 缺少 h1 正確回傳 None")

    # ------------------------------------------------------------------ #
    #  Test 6: HTML 結構遺漏價格圖表
    # ------------------------------------------------------------------ #
    @patch('cloudscraper.create_scraper')
    def test_missing_price_chart(self, mock_create_scraper):
        """有商品名稱但無價格資料時應回傳 None"""
        html = """<html><body>
        <h1 class="ts dividing big header">
            女 休閒長褲
            <div class="sub header">UNIQLO 商品編號 u0000000052430</div>
        </h1>
        <script>// no price chart here</script>
        </body></html>"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp
        mock_create_scraper.return_value = mock_session

        url = "https://uq.goodjack.tw/hmall-products/u0000000052430"
        result = get_product_data(url)

        self.assertIsNone(result)
        logger.success("[PASS] test_missing_price_chart — 缺少價格資料正確回傳 None")

    # ------------------------------------------------------------------ #
    #  Test 7: TocasUI v4 HTML 結構（ts-header）
    # ------------------------------------------------------------------ #
    @patch('cloudscraper.create_scraper')
    def test_tocas_v4_html_structure(self, mock_create_scraper):
        """TocasUI v4 的 ts-header 結構應正確解析商品名稱與價格"""
        price_rows = [
            ("2025-01-01", 2990),
            ("2025-03-01", 1990),
        ]
        html = _make_product_html_v4("男", "搖粒絨外套", "u0000000052992", price_rows)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp
        mock_create_scraper.return_value = mock_session

        url = "https://uq.goodjack.tw/hmall-products/u0000000052992"
        result = get_product_data(url)

        self.assertIsNotNone(result, "TocasUI v4 結構應成功解析")
        self.assertEqual(result['name'], "男 搖粒絨外套")
        self.assertEqual(result['original_price'], 2990.0)
        self.assertEqual(result['current_price'], 1990.0)
        self.assertEqual(result['status'], 'active')
        logger.success(f"[PASS] test_tocas_v4_html_structure — {result['name']} 折扣率 {result['discount_rate']:.2%}")

    # ------------------------------------------------------------------ #
    #  Test 8: 完全無 h1，退回 <title> 標籤解析
    # ------------------------------------------------------------------ #
    @patch('cloudscraper.create_scraper')
    def test_fallback_to_title_tag(self, mock_create_scraper):
        """找不到任何 h1 時，應從 <title> 解析商品名稱"""
        price_rows = [
            ("2025-01-01", 2490),
            ("2025-02-01", 1990),
        ]
        price_json = ", ".join(f'{{"t":"{r[0]}","y":{r[1]}}}' for r in price_rows)
        html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head><title>女 休閒短褲 | UQ 搜尋</title></head>
<body>
<canvas id="priceChart"></canvas>
<script>
    let ctx = document.getElementById("priceChart");
    let priceChart = new Chart(ctx, {{
        type: 'LineWithLine',
        data: {{
            datasets: [{{
                label: '價格',
                data: [{price_json}],
                backgroundColor: 'rgba(255, 255, 255, 0)',
                borderColor: 'rgba(206, 94, 87, 1.0)',
                borderWidth: 2,
            }}]
        }}
    }});
</script>
</body>
</html>"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp
        mock_create_scraper.return_value = mock_session

        url = "https://uq.goodjack.tw/hmall-products/u0000000053000"
        result = get_product_data(url)

        self.assertIsNotNone(result, "title fallback 應成功解析商品名稱")
        self.assertEqual(result['name'], "女 休閒短褲")
        self.assertEqual(result['original_price'], 2490.0)
        self.assertEqual(result['current_price'], 1990.0)
        self.assertEqual(result['status'], 'active')
        logger.success(f"[PASS] test_fallback_to_title_tag — {result['name']} 折扣率 {result['discount_rate']:.2%}")

    # ------------------------------------------------------------------ #
    #  Test 9: 已售罄商品
    # ------------------------------------------------------------------ #
    @patch('cloudscraper.create_scraper')
    def test_sold_out_product(self, mock_create_scraper):
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
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp
        mock_create_scraper.return_value = mock_session

        url = "https://uq.goodjack.tw/hmall-products/u0000000053269"
        result = get_product_data(url)

        self.assertIsNotNone(result, "應返回已售罄商品數據")
        self.assertEqual(result['status'], 'sold_out')
        self.assertEqual(result['name'], "女 輕便羽絨外套")
        self.assertEqual(result['url'], url)
        self.assertNotIn('discount_rate', result, "已售罄商品不應包含 discount_rate")
        logger.success(f"[PASS] test_sold_out_product — {result['name']} 狀態: {result['status']}")

    # ------------------------------------------------------------------ #
    #  Test 10: TocasUI v4 已售罄商品
    # ------------------------------------------------------------------ #
    @patch('cloudscraper.create_scraper')
    def test_sold_out_product_v4(self, mock_create_scraper):
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
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp
        mock_create_scraper.return_value = mock_session

        url = "https://uq.goodjack.tw/hmall-products/u0000000052992"
        result = get_product_data(url)

        self.assertIsNotNone(result)
        self.assertEqual(result['status'], 'sold_out')
        self.assertEqual(result['name'], "男 搖粒絨外套")
        logger.success(f"[PASS] test_sold_out_product_v4 — {result['name']} v4 結構檢測成功")


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("開始執行 get_product_data() 測試（使用 Mock HTML）")
    logger.info("=" * 60)
    unittest.main(verbosity=2)
