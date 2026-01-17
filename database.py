"""
database.py - Database management for LinkedIn Job Scraper
"""

import sqlite3
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class JobDatabase:
    """SQLite database manager for job tracking"""
    
    def __init__(self, db_file='jobs.db'):
        self.db_file = db_file
        self.conn = sqlite3.connect(db_file, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()
        logger.info(f"Database initialized: {db_file}")
    
    def create_tables(self):
        """Create database tables if they don't exist"""
        cursor = self.conn.cursor()
        
        # Jobs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                url TEXT UNIQUE,
                title TEXT,
                company TEXT,
                location TEXT,
                is_recommendation BOOLEAN,
                page INTEGER,
                first_seen TIMESTAMP,
                last_seen TIMESTAMP,
                times_seen INTEGER DEFAULT 1,
                notified BOOLEAN DEFAULT 0,
                notified_at TIMESTAMP
            )
        ''')
        
        # Scrape runs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scrape_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                duration_seconds REAL,
                jobs_found INTEGER,
                new_jobs INTEGER,
                notifications_sent INTEGER,
                errors INTEGER,
                pages_scraped INTEGER,
                status TEXT
            )
        ''')
        
        # Reports table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reports_sent (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_type TEXT,
                sent_at TIMESTAMP,
                period_start TIMESTAMP,
                period_end TIMESTAMP,
                jobs_included INTEGER
            )
        ''')
        
        # Create indexes for faster queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_company ON jobs(company)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_first_seen ON jobs(first_seen)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_notified ON jobs(notified)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_last_seen ON jobs(last_seen)')
        
        self.conn.commit()
        logger.debug("Database tables created/verified")
    
    def add_job(self, job_data):
        """
        Add new job or update existing one
        Returns True if job is new, False if it already exists
        """
        cursor = self.conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO jobs (job_id, url, title, company, location, is_recommendation, 
                                page, first_seen, last_seen, times_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            ''', (
                job_data['job_id'],
                job_data['url'],
                job_data['title'],
                job_data['company'],
                job_data['location'],
                job_data.get('is_recommendation', False),
                job_data.get('page', 1),
                job_data['scraped_at'],
                job_data['scraped_at']
            ))
            self.conn.commit()
            logger.debug(f"New job added: {job_data['job_id']}")
            return True  # New job
            
        except sqlite3.IntegrityError:
            # Job already exists, update last_seen and increment counter
            cursor.execute('''
                UPDATE jobs 
                SET last_seen = ?, times_seen = times_seen + 1
                WHERE job_id = ?
            ''', (job_data['scraped_at'], job_data['job_id']))
            self.conn.commit()
            logger.debug(f"Job updated: {job_data['job_id']}")
            return False  # Existing job
    
    def mark_notified(self, job_id):
        """Mark a job as notified"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE jobs 
            SET notified = 1, notified_at = ?
            WHERE job_id = ?
        ''', (datetime.now().isoformat(), job_id))
        self.conn.commit()
        logger.debug(f"Job marked as notified: {job_id}")
    
    def start_scrape_run(self):
        """Record the start of a scrape run, returns run ID"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO scrape_runs (started_at, status)
            VALUES (?, 'running')
        ''', (datetime.now().isoformat(),))
        self.conn.commit()
        run_id = cursor.lastrowid
        logger.info(f"Scrape run started: ID {run_id}")
        return run_id
    
    def complete_scrape_run(self, run_id, stats):
        """Record completion of scrape run"""
        cursor = self.conn.cursor()
        
        # Get start time to calculate duration
        started = cursor.execute(
            'SELECT started_at FROM scrape_runs WHERE id = ?', 
            (run_id,)
        ).fetchone()
        
        if started:
            start_time = datetime.fromisoformat(started['started_at'])
            duration = (datetime.now() - start_time).total_seconds()
        else:
            duration = 0
        
        cursor.execute('''
            UPDATE scrape_runs SET
                completed_at = ?,
                duration_seconds = ?,
                jobs_found = ?,
                new_jobs = ?,
                notifications_sent = ?,
                errors = ?,
                pages_scraped = ?,
                status = 'completed'
            WHERE id = ?
        ''', (
            datetime.now().isoformat(),
            duration,
            stats.get('jobs_found', 0),
            stats.get('new_jobs', 0),
            stats.get('notifications_sent', 0),
            stats.get('errors', 0),
            stats.get('pages_scraped', 0),
            run_id
        ))
        self.conn.commit()
        logger.info(f"Scrape run completed: ID {run_id}")
    
    def get_stats_for_period(self, hours=6):
        """Get statistics for a specific time period"""
        cursor = self.conn.cursor()
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        # Jobs in period
        jobs = cursor.execute('''
            SELECT * FROM jobs 
            WHERE first_seen >= ?
            ORDER BY first_seen DESC
        ''', (cutoff,)).fetchall()
        
        # Scrape runs in period
        runs = cursor.execute('''
            SELECT * FROM scrape_runs 
            WHERE started_at >= ? AND status = 'completed'
            ORDER BY started_at DESC
        ''', (cutoff,)).fetchall()
        
        return {
            'jobs': [dict(job) for job in jobs],
            'runs': [dict(run) for run in runs]
        }
    
    def record_report_sent(self, report_type, period_start, period_end, jobs_count):
        """Record that a report was sent"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO reports_sent (report_type, sent_at, period_start, period_end, jobs_included)
            VALUES (?, ?, ?, ?, ?)
        ''', (report_type, datetime.now().isoformat(), period_start, period_end, jobs_count))
        self.conn.commit()
        logger.debug(f"Report recorded: {report_type}")
    
    def get_total_stats(self):
        """Get all-time statistics"""
        cursor = self.conn.cursor()
        
        stats = {}
        
        # Total jobs
        stats['total_jobs'] = cursor.execute(
            'SELECT COUNT(*) as count FROM jobs'
        ).fetchone()['count']
        
        # Total companies
        stats['total_companies'] = cursor.execute(
            'SELECT COUNT(DISTINCT company) as count FROM jobs'
        ).fetchone()['count']
        
        # Total scrapes
        stats['total_scrapes'] = cursor.execute(
            'SELECT COUNT(*) as count FROM scrape_runs WHERE status = "completed"'
        ).fetchone()['count']
        
        # Notifications sent
        stats['total_notifications'] = cursor.execute(
            'SELECT COUNT(*) as count FROM jobs WHERE notified = 1'
        ).fetchone()['count']
        
        return stats
    
    def get_jobs_by_company(self, company_name):
        """Get all jobs from a specific company"""
        cursor = self.conn.cursor()
        jobs = cursor.execute('''
            SELECT * FROM jobs 
            WHERE company LIKE ?
            ORDER BY first_seen DESC
        ''', (f'%{company_name}%',)).fetchall()
        return [dict(job) for job in jobs]
    
    def get_recent_jobs(self, limit=10):
        """Get most recent jobs"""
        cursor = self.conn.cursor()
        jobs = cursor.execute('''
            SELECT * FROM jobs 
            ORDER BY first_seen DESC 
            LIMIT ?
        ''', (limit,)).fetchall()
        return [dict(job) for job in jobs]
    
    def close(self):
        """Close database connection"""
        try:
            self.conn.close()
            logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database: {e}")