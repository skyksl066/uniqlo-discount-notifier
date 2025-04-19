# -*- coding: utf-8 -*-
"""
Created on Sat Apr 19 12:17:55 2025

@author: Alex
"""

import os
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from loguru import logger
from datetime import datetime
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def open_browser():
    """初始化並返回一個Chrome瀏覽器實例"""
    options = webdriver.ChromeOptions()
    if 'SPYDER_ARGS' not in os.environ:
        options.add_argument('--headless')  # 啟動無頭模式
    options.add_argument("--log-level=1")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    return webdriver.Chrome(options=options)


def post_message(client, channel, text):
    """發送消息到Slack"""
    try:
        client.chat_postMessage(channel=channel, text=text)
        logger.success(f"Message sent to channel: {channel}")
    except SlackApiError as e:
        logger.error(f"Error sending message: {e}")


def get_product_data(driver, url):
    """獲取產品數據"""
    try:
        driver.get(url.strip())
        logger.info(f'Accessing: {url.strip()}')

        # 等待頁面加載完成
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'priceChart')))

        # 獲取商品名稱
        product_name = driver.find_element(By.CSS_SELECTOR, 'h1.ts.dividing.big.header').text
        logger.info(f'Product: {product_name}')

        # 獲取價格數據
        price_data = driver.execute_script("return priceChart.data.datasets[0].data;")
        prices = [float(data['y']) for data in price_data]

        # 計算價格信息
        max_price = max(prices)
        min_price = min(prices)
        current_price = prices[-1]
        discount_rate = (max_price - current_price) / max_price

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

    driver = open_browser()
    qualified_products = []

    try:
        # 處理每個產品 URL
        for url in urls:
            if not url.strip():
                continue

            product_data = get_product_data(driver, url)
            if product_data:
                qualified_products.append(product_data)
    finally:
        # 確保瀏覽器總是被關閉
        driver.quit()
        logger.info('Browser closed')

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
    log_path = f'Logs/{datetime.today().strftime("%Y%m%d")}.log'
    logger.add(log_path, rotation='1 day', level='INFO')

    main()
