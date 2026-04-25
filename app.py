# -*- coding: utf-8 -*-
"""
Created on Sat Apr 19 12:17:55 2025

@author: Alex
"""

import os
import sys
import re
import json
import time
import requests
from bs4 import BeautifulSoup
from loguru import logger
from datetime import datetime
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def post_message(client, channel, text):
    """發送消息到Slack"""
    try:
        client.chat_postMessage(channel=channel, text=text)
        logger.success(f"Message sent to channel: {channel}")
    except SlackApiError as e:
        logger.error(f"Error sending message: {e}")


def get_product_data(url, session=None):
    """獲取產品數據"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }

        http_client = session if session is not None else requests
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

    # 使用 Session 保持 cookie 並讓伺服器識別為合法瀏覽器
    session = requests.Session()

    # 處理每個產品 URL
    for url in urls:
        if not url.strip():
            continue

        product_data = get_product_data(url, session=session)
        if product_data:
            qualified_products.append(product_data)
        time.sleep(1)

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


if __name__ == '__main__':
    # 設置日誌
    import pathlib
    log_dir = pathlib.Path('Logs')
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / f'{datetime.today().strftime("%Y%m%d")}.log'
    logger.add(str(log_path), rotation='1 day', level='INFO')

    main()
