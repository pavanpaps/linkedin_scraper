# LinkedIn Job Scraper

An automated LinkedIn job scraper that monitors job postings and sends Telegram notifications for new opportunities.

## Features

- 🔍 Automated job search on LinkedIn
- 📱 Real-time Telegram notifications
- 🗄️ SQLite database for job tracking
- 📊 Detailed analytics and reports
- 🎯 Customizable filters (keywords, companies, locations)
- 🔄 Continuous monitoring with configurable intervals
- 🚫 Duplicate detection
- 📈 Periodic and daily summary reports

## Prerequisites

- Python 3.8+
- Chrome browser
- ChromeDriver
- Telegram Bot Token
- LinkedIn account

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/linkedin-job-scraper.git
cd linkedin-job-scraper
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create configuration file:
```bash
cp config.example.json config.json
```

5. Edit `config.json` with your credentials and preferences

## Configuration

Edit `config.json`:
```json
{
  "linkedin": {
    "email": "your-email@example.com",
    "password": "your-password"
  },
  "telegram": {
    "bot_token": "your-bot-token",
    "chat_id": "your-chat-id"
  },
  "job_search": {
    "keywords": "Data Engineer",
    "location": "Bengaluru, Karnataka, India",
    "time_filter": "r86400"
  },
  "filters": {
    "required_keywords": ["python", "data"],
    "excluded_keywords": ["senior", "lead"],
    "min_notifications_per_run": 1
  }
}
```

## Usage

### Basic Usage
```bash
python main.py
```

### Run with custom interval
```bash
python main.py --interval 60  # Check every 60 minutes
```

### Headless mode
```bash
python main.py --headless
```

## Features Detail

### Job Filtering
- Required keywords
- Excluded keywords
- Company blacklist/whitelist
- Location filtering

### Notifications
- Individual job notifications
- Batch notifications
- Error alerts
- Health checks
- Daily summaries

### Database
- Job tracking
- Scrape run history
- Statistics
- Report generation

## Troubleshooting

### Login Issues
- Ensure credentials are correct in `config.json`
- LinkedIn may require manual verification
- Check if cookies file exists

### ChromeDriver Issues
- Ensure ChromeDriver version matches Chrome browser
- Add ChromeDriver to system PATH

### No Jobs Found
- Adjust search filters
- Check LinkedIn search URL
- Verify location format

## Security Notes

⚠️ **IMPORTANT**: Never commit these files:
- `config.json` (contains credentials)
- `*.pkl` files (cookies)
- `*.db` files (contains scraped data)

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## License

This project is for educational purposes only. Please respect LinkedIn's Terms of Service.

## Disclaimer

This tool is for personal use only. Use responsibly and in accordance with LinkedIn's terms of service. The authors are not responsible for any misuse or violations.
