#!/usr/bin/env python3
"""
Scheduler script for Member Moments app.
Runs the main application at specified intervals.
"""

import schedule
import time
import subprocess
import sys
import os
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)

def run_member_moments():
    """Run the Member Moments application"""
    try:
        logging.info("Starting Member Moments run...")
        
        # Run the main application
        result = subprocess.run([
            sys.executable, '-m', 'src.main',
            '--csv', 'companies_with_locations.csv',
            '--config', 'config.yaml',
            '--since_days', '1'
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        if result.returncode == 0:
            logging.info("Member Moments run completed successfully")
            if result.stdout:
                logging.info(f"Output: {result.stdout}")
        else:
            logging.error(f"Member Moments run failed with return code {result.returncode}")
            if result.stderr:
                logging.error(f"Error: {result.stderr}")
                
    except Exception as e:
        logging.error(f"Exception occurred while running Member Moments: {e}")

def main():
    """Main scheduler function"""
    logging.info("Starting Member Moments scheduler...")
    
    # Schedule jobs
    schedule.every().day.at("09:00").do(run_member_moments)  # Daily at 9 AM
    schedule.every().day.at("17:00").do(run_member_moments)  # Daily at 5 PM
    
    # You can add more schedules here:
    # schedule.every().hour.do(run_member_moments)
    # schedule.every().monday.at("10:00").do(run_member_moments)
    
    logging.info("Scheduled jobs:")
    for job in schedule.get_jobs():
        logging.info(f"  - {job}")
    
    # Run once immediately
    logging.info("Running initial job...")
    run_member_moments()
    
    # Keep the scheduler running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main()
