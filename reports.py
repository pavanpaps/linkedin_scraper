"""
reports.py - Report generation for LinkedIn Job Scraper
"""

from datetime import datetime, timedelta
from collections import Counter, defaultdict
import logging

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generate various reports for Telegram notifications"""
    
    def __init__(self, db):
        self.db = db
    
    def format_duration(self, seconds):
        """Format duration in human readable form"""
        if seconds < 60:
            return f"{int(seconds)}s"
        minutes = int(seconds / 60)
        secs = int(seconds % 60)
        if minutes < 60:
            return f"{minutes}m {secs}s"
        hours = int(minutes / 60)
        mins = int(minutes % 60)
        return f"{hours}h {mins}m"
    
    def generate_run_report(self, run_stats, jobs_data):
        """
        Generate per-run report (sent after each scrape)
        
        Args:
            run_stats: Dictionary with run statistics
            jobs_data: List of job dictionaries found in this run
        
        Returns:
            Formatted HTML message for Telegram
        """
        duration = self.format_duration(run_stats.get('duration', 0))
        
        # Count job types
        direct_matches = sum(1 for j in jobs_data if not j.get('is_recommendation'))
        recommendations = sum(1 for j in jobs_data if j.get('is_recommendation'))
        
        # Top companies
        companies = Counter(
            j['company'] for j in jobs_data 
            if j['company'] and j['company'] != 'Not specified'
        )
        top_companies = companies.most_common(5)
        
        # Build report
        report = f"""
🔍 <b>Scrape Run Complete</b>

⏱️ <b>Duration:</b> {duration}
📄 <b>Pages Scraped:</b> {run_stats.get('pages_scraped', 0)}
📊 <b>Jobs Found:</b> {run_stats.get('jobs_found', 0)} jobs
  ├─ Direct Matches: {direct_matches}
  └─ Recommendations: {recommendations}

🆕 <b>New Jobs:</b> {run_stats.get('new_jobs', 0)} jobs
📨 <b>Notifications Sent:</b> {run_stats.get('notifications_sent', 0)}
"""
        
        # Add top companies if any
        if top_companies:
            report += "\n🏢 <b>Top Companies:</b>\n"
            for i, (company, count) in enumerate(top_companies, 1):
                report += f"  {i}. {company} - {count} job{'s' if count > 1 else ''}\n"
        
        # Add match rate
        if run_stats.get('jobs_found', 0) > 0:
            match_rate = (direct_matches / run_stats['jobs_found']) * 100
            report += f"\n🎯 <b>Match Rate:</b> {match_rate:.0f}% ({direct_matches}/{run_stats['jobs_found']})"
        
        report += f"\n\n⏰ <i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
        
        return report
    
    def generate_periodic_report(self, hours=6):
        """
        Generate periodic summary report (e.g., every 6 hours)
        
        Args:
            hours: Number of hours to look back
        
        Returns:
            Formatted HTML message for Telegram, or None if no activity
        """
        period_data = self.db.get_stats_for_period(hours)
        jobs = period_data['jobs']
        runs = period_data['runs']
        
        if not jobs and not runs:
            logger.info(f"No activity in last {hours} hours")
            return None  # No activity in period
        
        # Calculate stats
        total_runs = len(runs)
        total_jobs = sum(r['jobs_found'] for r in runs)
        new_jobs = len(jobs)
        notifications = sum(r['notifications_sent'] for r in runs)
        
        # Top companies
        companies = Counter(
            j['company'] for j in jobs 
            if j['company'] and j['company'] != 'Not specified'
        )
        top_companies = companies.most_common(5)
        
        # Top locations (just city name)
        locations = Counter(
            j['location'].split(',')[0].strip() for j in jobs
            if j['location']
        )
        top_locations = locations.most_common(3)
        
        # Peak hours (when most jobs were found)
        hour_counts = defaultdict(int)
        for job in jobs:
            try:
                hour = datetime.fromisoformat(job['first_seen']).hour
                hour_counts[hour] += 1
            except:
                pass
        
        peak_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Build report
        period_str = f"{hours}-Hour" if hours < 24 else "Daily"
        start_time = (datetime.now() - timedelta(hours=hours)).strftime('%I:%M %p')
        end_time = datetime.now().strftime('%I:%M %p')
        
        report = f"""
📊 <b>{period_str} Summary Report</b>
<i>Period: {start_time} - {end_time}</i>

📈 <b>Activity</b>
  • Scrape Runs: {total_runs}
  • Total Jobs Seen: {total_jobs}
  • New Jobs: {new_jobs}
  • Notifications: {notifications}
"""
        
        # Add top companies
        if top_companies:
            report += "\n🏢 <b>Top Companies (New Jobs)</b>\n"
            for i, (company, count) in enumerate(top_companies, 1):
                report += f"  {i}. {company}: {count} job{'s' if count > 1 else ''}\n"
        
        # Add top locations
        if top_locations:
            report += "\n📍 <b>Top Locations</b>\n"
            for i, (location, count) in enumerate(top_locations, 1):
                report += f"  {i}. {location}: {count} job{'s' if count > 1 else ''}\n"
        
        # Add peak hours
        if peak_hours:
            report += "\n⏰ <b>Peak Hours</b>\n"
            for hour, count in peak_hours:
                time_str = datetime.strptime(f"{hour:02d}:00", "%H:%M").strftime("%I:%M %p")
                report += f"  • {time_str}: {count} new job{'s' if count > 1 else ''}\n"
        
        # Add best matches (non-recommendations)
        best_matches = [j for j in jobs if not j['is_recommendation']][:5]
        if best_matches:
            report += "\n🎯 <b>Best Matches</b>\n"
            for job in best_matches:
                company = job['company'] if job['company'] != 'Not specified' else ''
                separator = ' - ' if company else ''
                title = job['title'][:40] + '...' if len(job['title']) > 40 else job['title']
                report += f"  ⭐ {title}{separator}{company}\n"
        
        report += f"\n⏰ <i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
        
        return report
    
    def generate_daily_summary(self):
        """
        Generate comprehensive daily summary report
        
        Returns:
            Formatted HTML message for Telegram
        """
        period_data = self.db.get_stats_for_period(hours=24)
        total_stats = self.db.get_total_stats()
        
        jobs_today = period_data['jobs']
        runs_today = period_data['runs']
        
        total_jobs_today = sum(r['jobs_found'] for r in runs_today)
        new_jobs_today = len(jobs_today)
        
        report = f"""
📅 <b>Daily Summary - {datetime.now().strftime('%b %d, %Y')}</b>

📊 <b>Today's Stats</b>
  • Total Scrapes: {len(runs_today)}
  • Jobs Discovered: {total_jobs_today}
  • New Opportunities: {new_jobs_today}
  • Notifications Sent: {sum(r['notifications_sent'] for r in runs_today)}

📈 <b>All-Time Stats</b>
  • Total Jobs Tracked: {total_stats['total_jobs']}
  • Companies Seen: {total_stats['total_companies']}
  • Total Scrapes: {total_stats['total_scrapes']}
  • Total Notifications: {total_stats['total_notifications']}
"""
        
        # Top companies today
        companies = Counter(
            j['company'] for j in jobs_today 
            if j['company'] and j['company'] != 'Not specified'
        )
        
        if companies:
            report += "\n🏢 <b>Top Companies Today</b>\n"
            for i, (company, count) in enumerate(companies.most_common(3), 1):
                report += f"  {i}. {company} - {count} job{'s' if count > 1 else ''}\n"
        
        report += f"\n⏰ <i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
        
        return report
    
    def generate_simple_summary(self, current_jobs, pages_scraped):
        """
        Generate a simple summary for quick updates
        
        Args:
            current_jobs: List of jobs found in current run
            pages_scraped: Number of pages scraped
        
        Returns:
            Formatted HTML message for Telegram
        """
        if not current_jobs:
            return None
        
        direct_matches = sum(1 for j in current_jobs if not j.get('is_recommendation'))
        
        # Top companies
        companies = Counter(
            j['company'] for j in current_jobs 
            if j['company'] and j['company'] != 'Not specified'
        )
        top_companies = companies.most_common(3)
        
        message = f"""
🔍 <b>Scrape Complete</b>

📄 <b>Pages:</b> {pages_scraped}
📊 <b>Jobs Found:</b> {len(current_jobs)}
  ├─ Direct: {direct_matches}
  └─ Recommended: {len(current_jobs) - direct_matches}
"""
        
        if top_companies:
            message += "\n🏢 <b>Top Companies:</b>\n"
            for company, count in top_companies:
                message += f"  • {company} ({count})\n"
        
        message += f"\n⏰ {datetime.now().strftime('%I:%M %p')}"
        
        return message