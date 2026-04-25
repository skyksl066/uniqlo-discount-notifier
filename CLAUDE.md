# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**UNIQLO Discount Notifier** — Monitors UNIQLO product prices on goodjack.tw and sends Slack notifications for discounts.

**Architecture**: 
1. Fetch HTML from product URLs using `cloudscraper` (handles CloudFlare protection)
2. Parse product name and price history with BeautifulSoup
3. Batch results and send Slack messages

**Key Features**:
- Automatic CloudFlare JS challenge solving (no browser needed)
- Resilient HTML parsing (handles TocasUI v3/v4 structure changes)
- Runs on GitHub Actions schedule: Thu-Sat at 3 UTC (11 AM UTC+8)
- Logs daily to `Logs/YYYYMMDD.log`

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the notifier
export SLACK_TOKEN="xoxb-your-token"
export SLACK_CHANNEL="#your-channel"
python app.py

# Run tests
python -m unittest test_app.py
# or single test:
python -m unittest test_app.TestGetProductData.test_discounted_product
```

## Dependencies

- `cloudscraper`: HTTP client with automatic CloudFlare JS challenge solving
- `brotli`: Decompression for Brotli-encoded HTTP responses
- `beautifulsoup4`: HTML parsing
- `loguru`: Structured logging with file rotation (daily logs in `Logs/` directory)
- `slack_sdk`: Official Slack SDK for message posting


## Known Issues & Solutions

### ⚠️ CloudFlare Challenge (403 Forbidden)

**Problem**: The target site (uq.goodjack.tw) uses CloudFlare protection which returns "Just a moment..." challenge pages. Standard `requests` library cannot solve these JavaScript challenges, resulting in 403 Forbidden errors—especially in GitHub Actions environment.

**Previous Failed Attempts**:
- ❌ **Selenium**: Chromium crashes in GitHub Actions (headless Linux environment lacks X11, missing system dependencies, insufficient resources)
- ❌ **requests + retry**: CloudFlare detects and blocks GitHub Actions IP at CloudFlare level; retries don't help
- ❌ **requests + enhanced headers**: Even with Referer, Sec-Fetch headers, User-Agent spoofing—CloudFlare still blocks

**Solution**: Use `cloudscraper` library
- Automatically detects and solves CloudFlare JS challenges without a browser
- Works reliably in GitHub Actions (lightweight, no external dependencies beyond `brotli`)
- API compatible with `requests` (drop-in replacement)

**Implementation**:
```python
import cloudscraper
scraper = cloudscraper.create_scraper()
response = scraper.get(url, headers=headers)
# cloudscraper automatically handles CloudFlare challenge
```

**Dependencies**: `cloudscraper` + `brotli` (for Brotli decompression)

**Why This Works**: CloudFlare's JS challenge can be solved mathematically without executing JavaScript in a browser. `cloudscraper` implements this algorithm in pure Python.

---

### ⚠️ Brotli Encoding

**Problem**: Server returns `Content-Encoding: br` (Brotli). Without the `brotli` library, responses decode as garbage characters (replacement character `�`).

**Solution**: Add `brotli` to requirements. Both `requests` and `cloudscraper` will auto-decompress when installed.

**Note**: Even if using `cloudscraper`, you must include `brotli` in dependencies.

---

## Setup & Configuration

- **Product List**: Edit `data/product_list.txt` — one UNIQLO URL per line
- **Logs**: Auto-created in `Logs/` directory (daily rotation via loguru)
- **GitHub Actions**: Requires `SLACK_TOKEN` and `SLACK_CHANNEL` secrets in repository settings
- **Python Version**: 3.10+
