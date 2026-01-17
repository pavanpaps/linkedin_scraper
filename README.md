# LinkedIn Job Scraper

A robust, automated tool designed to scrape LinkedIn job postings, filter them based on custom criteria, and send real-time notifications via Telegram. This project helps job seekers automate their search process, ensuring they never miss a relevant opportunity.

## 🚀 Features

* **Automated Scraping**: Periodically searches LinkedIn for jobs matching your criteria.
* **Smart Filtering**:
    * **Required Keywords**: Only keep jobs containing specific terms (e.g., "Python", "Remote").
    * **Excluded Keywords**: Automatically discard jobs with unwanted terms (e.g., "Senior", "Intern").
* **Instant Notifications**: Sends alerts to your Telegram with job titles, companies, and direct application links.
* **Duplicate Detection**: Uses a local SQLite database to track seen jobs and prevent duplicate alerts.
* **Headless Mode**: Can run in the background (headless Chrome), making it suitable for deployment on servers or VPS.
* **Reporting**: Includes a dashboard and reporting module to analyze scraped job data.
* **Resiliency**: Includes process management (`pid_manager.py`) to handle cron jobs and prevent overlapping instances.

## 📂 Project Structure

| File | Description |
| :--- | :--- |
| `main.py` | Entry point. initializes the scraper, runs the job search, and triggers notifications. |
| `config.json` | (Created from `config.example.json`) Stores credentials and search preferences. |
| `linkedin_scraper.py` | Core logic for navigating LinkedIn and handling the browser session. |
| `job_extractor.py` | Parses HTML to extract job details (Title, Company, Location, URL). |
| `job_filters.py` | Applies whitelist/blacklist logic to filtered jobs. |
| `notifications.py` | Handles Telegram API integration for sending alerts. |
| `database.py` | Manages SQLite connection for storing job history. |
| `web_driver.py` | Configures Selenium WebDriver (Chrome options, User-Agents). |
| `dashboard.html` | Frontend interface for viewing job statistics and reports. |

## 🛠️ Prerequisites

Before you begin, ensure you have the following installed:

* **Python 3.8+**
* **Google Chrome** (Latest version)
* **ChromeDriver** (Matches your Chrome version)
* **Telegram Bot Token**: Get this from [@BotFather](https://t.me/botfather) on Telegram.
* **LinkedIn Account**: *Recommended to use a secondary account.*

## 📥 Installation

1.  **Clone the Repository**
    ```bash
    git clone [https://github.com/pavanpaps/linkedin_scraper.git](https://github.com/pavanpaps/linkedin_scraper.git)
    cd linkedin_scraper
    ```

2.  **Create a Virtual Environment**
    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\activate

    # macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Setup Configuration**
    Copy the example config file and edit it.
    ```bash
    cp config.example.json config.json
    ```

## ⚙️ Configuration

Open `config.json` and update the following fields:

```json
{
  "linkedin": {
    "email": "YOUR_LINKEDIN_EMAIL",
    "password": "YOUR_LINKEDIN_PASSWORD"
  },
  "telegram": {
    "bot_token": "YOUR_TELEGRAM_BOT_TOKEN",
    "chat_id": "YOUR_TELEGRAM_CHAT_ID"
  },
  "job_search": {
    "keywords": "Data Scientist",
    "location": "New York, USA",
    "time_filter": "r86400" 
  },
  "filters": {
    "required_keywords": ["python", "machine learning"],
    "excluded_keywords": ["senior", "principal", "staff"],
    "min_notifications_per_run": 1
  }
}