# UNIQLO Discount Notifier

A Python automation script that monitors UNIQLO product prices and sends notifications to Slack when discounts are available.

## Features
- Track multiple UNIQLO products from a list
- Extract current and historical price data
- Calculate discount rates automatically
- Send organized notifications to Slack

## Requirements
- Python 3.6+
- Chrome browser
- Selenium
- Slack API access

## Installation
1. Clone this repository:
```bash
git clone https://github.com/skyksl066/uniqlo-discount-notifier.git
cd uniqlo-discount-notifier
```
2. Install required packages:
```bash
pip install -r requirements.txt
```
3. Download and install ChromeDriver that matches your Chrome browser version
4. Create a data folder and add your product URLs to data/product_list.txt, one URL per line

## Usage
Run the script with your Slack API token as a command line argument:
```bash
export SLACK_TOKEN="your-slack-token-here"
export SLACK_CHANNEL="your-slack-channel-here"
python uniqloDiscountNotifier.py
```

## How It Works
The script:
1. Opens each product URL in a headless Chrome browser
2. Extracts product name and price history data
3. Calculates original price (highest), current price, and discount rate
4. Organizes products into groups of three
5. Sends formatted notifications to your specified Slack channel

## Customizing
To change the Slack channel, modify the channel name in the post_message function call
Adjust the number of products per notification by changing the unit_size variable
You can modify the message format in the notification section

## Security Note
This script uses command-line arguments for the Slack token to avoid hardcoded credentials. Never commit your actual token to version control.

## License
MIT License - See the LICENSE file for details
