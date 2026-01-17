"""
test_setup.py - Test if everything is set up correctly
Run this before running main.py to verify your installation
"""

import sys
import os

print("=" * 60)
print("Enhanced LinkedIn Job Scraper - Setup Test")
print("=" * 60)
print()

# Test 1: Python version
print("[1/8] Testing Python version...")
python_version = sys.version_info
if python_version.major >= 3 and python_version.minor >= 8:
    print(f"  ✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
else:
    print(f"  ❌ Python version too old: {python_version.major}.{python_version.minor}")
    print("  Please upgrade to Python 3.8 or higher")
    sys.exit(1)

# Test 2: Required modules
print("\n[2/8] Testing required packages...")
required_packages = {
    'requests': 'requests',
    'bs4': 'beautifulsoup4',
    'selenium': 'selenium',
    'webdriver_manager': 'webdriver-manager'
}

missing_packages = []
for module_name, package_name in required_packages.items():
    try:
        __import__(module_name)
        print(f"  ✅ {package_name}")
    except ImportError:
        print(f"  ❌ {package_name} not installed")
        missing_packages.append(package_name)

if missing_packages:
    print("\n  Install missing packages with:")
    print(f"  pip install {' '.join(missing_packages)}")
    sys.exit(1)

# Test 3: Required files
print("\n[3/8] Testing required files...")
required_files = [
    'job_bot_edited.py',
    'database.py',
    'reports.py',
    'scraper.py',
    'main.py'
]

missing_files = []
for filename in required_files:
    if os.path.exists(filename):
        print(f"  ✅ {filename}")
    else:
        print(f"  ❌ {filename} not found")
        missing_files.append(filename)

if missing_files:
    print("\n  Please make sure all files are in the same directory!")
    sys.exit(1)

# Test 4: Import custom modules
print("\n[4/8] Testing custom modules...")
try:
    from database import JobDatabase
    print("  ✅ database.py")
except Exception as e:
    print(f"  ❌ database.py - Error: {e}")
    sys.exit(1)

try:
    from reports import ReportGenerator
    print("  ✅ reports.py")
except Exception as e:
    print(f"  ❌ reports.py - Error: {e}")
    sys.exit(1)

try:
    from scraper import EnhancedJobScraper
    print("  ✅ scraper.py")
except Exception as e:
    print(f"  ❌ scraper.py - Error: {e}")
    sys.exit(1)

# Test 5: Import original scraper
print("\n[5/8] Testing original scraper...")
try:
    from job_bot_edited import LinkedInJobScraper
    print("  ✅ job_bot_edited.py")
except Exception as e:
    print(f"  ❌ job_bot_edited.py - Error: {e}")
    print("  Make sure your original scraper file is named job_bot_edited.py")
    sys.exit(1)

# Test 6: Config file
print("\n[6/8] Testing configuration...")
if os.path.exists('config.json'):
    print("  ✅ config.json exists")
    
    # Check if config is valid
    try:
        import json
        with open('config.json', 'r') as f:
            config = json.load(f)
        
        required_fields = ['telegram_bot_token', 'telegram_chat_id', 'linkedin_email', 'linkedin_password']
        has_placeholder = False
        
        for field in required_fields:
            if not config.get(field):
                print(f"  ⚠️  {field} is empty")
                has_placeholder = True
            elif 'YOUR_' in str(config[field]).upper():
                print(f"  ⚠️  {field} has placeholder value")
                has_placeholder = True
        
        if has_placeholder:
            print("\n  Please update config.json with your actual credentials")
        else:
            print("  ✅ All required fields are configured")
    
    except Exception as e:
        print(f"  ❌ Error reading config.json: {e}")

else:
    print("  ⚠️  config.json not found")
    print("  It will be created automatically on first run")

# Test 7: Database creation
print("\n[7/8] Testing database creation...")
try:
    test_db = JobDatabase('test_jobs.db')
    print("  ✅ Database can be created")
    test_db.close()
    os.remove('test_jobs.db')
    print("  ✅ Database test file cleaned up")
except Exception as e:
    print(f"  ❌ Database creation failed: {e}")
    sys.exit(1)

# Test 8: Selenium WebDriver
print("\n[8/8] Testing Selenium WebDriver...")
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    
    print("  ✅ Selenium modules loaded")
    print("  ℹ️  ChromeDriver will be auto-downloaded on first run")
    
except Exception as e:
    print(f"  ❌ Selenium test failed: {e}")
    sys.exit(1)

# All tests passed!
print("\n" + "=" * 60)
print("✅ All tests passed! Your setup is ready.")
print("=" * 60)
print("\nNext steps:")
print("1. Make sure config.json has your credentials")
print("2. Run: python main.py")
print("\nHappy job hunting! 🎯")
print()