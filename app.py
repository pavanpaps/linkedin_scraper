"""
app.py - Flask Web Dashboard for LinkedIn Job Scraper
Fixed: Accurate scraper status detection
"""

from flask import Flask, send_file, jsonify, request
import sqlite3
from datetime import datetime, timedelta
import logging
import os
import psutil
import io

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Database file path
DB_FILE = 'jobs.db'

# Store the scraper PID for accurate tracking
SCRAPER_PID_FILE = '.scraper.pid'


def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def is_scraper_running():
    """
    Check if main.py scraper is actually running
    Uses PID file and process verification for accuracy
    """
    # Method 1: Check PID file
    if os.path.exists(SCRAPER_PID_FILE):
        try:
            with open(SCRAPER_PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            
            # Verify process still exists and is the scraper
            try:
                proc = psutil.Process(pid)
                cmdline = ' '.join(proc.cmdline())
                
                # Check if it's actually the scraper
                if 'main.py' in cmdline or 'linkedin_scraper' in cmdline:
                    # Make sure it's not this dashboard app
                    if 'app.py' not in cmdline:
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # Process doesn't exist, clean up stale PID file
                os.remove(SCRAPER_PID_FILE)
                return False
        except Exception as e:
            logger.debug(f"Error reading PID file: {e}")
    
    # Method 2: Check last scrape run time (fallback)
    # If scraper ran in last 15 minutes, consider it "running"
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        last_run = cursor.execute('''
            SELECT started_at FROM scrape_runs 
            WHERE status = 'running' OR 
                  (status = 'completed' AND datetime(completed_at) > datetime('now', '-15 minutes'))
            ORDER BY started_at DESC 
            LIMIT 1
        ''').fetchone()
        conn.close()
        
        if last_run:
            return True
    except:
        pass
    
    return False


@app.route('/')
def index():
    """Main dashboard page"""
    # Serve the HTML file directly
    return send_file(io.BytesIO(DASHBOARD_HTML.encode()), mimetype='text/html')


@app.route('/api/stats')
def get_stats():
    """Get overall statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Total stats
        total_jobs = cursor.execute('SELECT COUNT(*) as count FROM jobs').fetchone()['count']
        
        total_companies = cursor.execute(
            'SELECT COUNT(DISTINCT company) as count FROM jobs WHERE company != "Not specified"'
        ).fetchone()['count']
        
        total_scrapes = cursor.execute(
            'SELECT COUNT(*) as count FROM scrape_runs WHERE status = "completed"'
        ).fetchone()['count']
        
        total_notifications = cursor.execute(
            'SELECT COUNT(*) as count FROM jobs WHERE notified = 1'
        ).fetchone()['count']
        
        # Today's stats
        today_start = datetime.now().replace(hour=0, minute=0, second=0).isoformat()
        
        jobs_today = cursor.execute(
            'SELECT COUNT(*) as count FROM jobs WHERE first_seen >= ?',
            (today_start,)
        ).fetchone()['count']
        
        runs_today = cursor.execute(
            'SELECT COUNT(*) as count FROM scrape_runs WHERE started_at >= ? AND status = "completed"',
            (today_start,)
        ).fetchone()['count']
        
        conn.close()
        
        # Check scraper status (accurate)
        scraper_running = is_scraper_running()
        
        return jsonify({
            'success': True,
            'total_jobs': total_jobs,
            'total_companies': total_companies,
            'total_scrapes': total_scrapes,
            'total_notifications': total_notifications,
            'jobs_today': jobs_today,
            'runs_today': runs_today,
            'scraper_running': scraper_running
        })
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/recent-jobs')
def get_recent_jobs():
    """Get recent jobs with sorting"""
    try:
        limit = request.args.get('limit', 50, type=int)
        sort_by = request.args.get('sort', 'first_seen')
        order = request.args.get('order', 'desc')
        
        # Validate
        allowed_sorts = ['first_seen', 'company', 'title', 'location']
        if sort_by not in allowed_sorts:
            sort_by = 'first_seen'
        
        if order not in ['asc', 'desc']:
            order = 'desc'
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = f'SELECT * FROM jobs ORDER BY {sort_by} {order.upper()} LIMIT ?'
        jobs = cursor.execute(query, (limit,)).fetchall()
        
        result = [dict(job) for job in jobs]
        conn.close()
        
        return jsonify({
            'success': True,
            'jobs': result
        })
    except Exception as e:
        logger.error(f"Error getting recent jobs: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/jobs-by-company')
def get_jobs_by_company():
    """Get jobs grouped by company"""
    try:
        limit = request.args.get('limit', 12, type=int)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        companies = cursor.execute(f'''
            SELECT company, COUNT(*) as count 
            FROM jobs 
            WHERE company != 'Not specified'
            GROUP BY company 
            ORDER BY count DESC 
            LIMIT ?
        ''', (limit,)).fetchall()
        
        result = [{'company': row['company'], 'count': row['count']} for row in companies]
        conn.close()
        
        return jsonify({
            'success': True,
            'companies': result
        })
    except Exception as e:
        logger.error(f"Error getting companies: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/recent-runs')
def get_recent_runs():
    """Get recent scrape runs"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        runs = cursor.execute('''
            SELECT * FROM scrape_runs 
            WHERE status = 'completed'
            ORDER BY started_at DESC 
            LIMIT 10
        ''').fetchall()
        
        result = [dict(row) for row in runs]
        conn.close()
        
        return jsonify({
            'success': True,
            'runs': result
        })
    except Exception as e:
        logger.error(f"Error getting runs: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/search-jobs')
def search_jobs():
    """Search jobs by keyword"""
    try:
        query = request.args.get('q', '')
        
        if not query:
            return jsonify({'success': True, 'jobs': []})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        jobs = cursor.execute('''
            SELECT * FROM jobs
            WHERE title LIKE ? OR company LIKE ? OR location LIKE ?
            ORDER BY first_seen DESC
            LIMIT 50
        ''', (f'%{query}%', f'%{query}%', f'%{query}%')).fetchall()
        
        result = [dict(job) for job in jobs]
        conn.close()
        
        return jsonify({
            'success': True,
            'jobs': result
        })
    except Exception as e:
        logger.error(f"Error searching jobs: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/test')
def test():
    """Test endpoint"""
    return jsonify({
        'success': True,
        'message': 'API is working',
        'timestamp': datetime.now().isoformat(),
        'scraper_running': is_scraper_running()
    })


# Embed HTML directly (no template folder needed)
DASHBOARD_HTML = open('dashboard.html', 'r', encoding='utf-8').read() if os.path.exists('dashboard.html') else """
<!DOCTYPE html>
<html><body><h1>Dashboard HTML not found</h1><p>Please ensure dashboard.html exists in the same directory.</p></body></html>
"""


if __name__ == '__main__':
    print("=" * 60)
    print("LinkedIn Job Scraper - Dashboard")
    print("=" * 60)
    
    # Check database
    if not os.path.exists(DB_FILE):
        print(f"\n⚠️  Database not found: {DB_FILE}")
        print("   Run the scraper first: python main.py")
    else:
        print(f"\n✅ Database: {DB_FILE}")
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            job_count = cursor.execute('SELECT COUNT(*) as count FROM jobs').fetchone()['count']
            print(f"   Jobs: {job_count}")
            conn.close()
        except Exception as e:
            print(f"   Error: {e}")
    
    # Check scraper status
    if is_scraper_running():
        print("\n✅ Scraper: RUNNING")
    else:
        print("\n⚠️  Scraper: STOPPED")
        print("   Start with: python main.py")
    
    print("\n🌐 Dashboard: http://localhost:5000")
    print("🔗 API Test: http://localhost:5000/api/test")
    print("🛑 Press Ctrl+C to stop\n")
    
    # Run Flask
    app.run(debug=True, host='0.0.0.0', port=5000)