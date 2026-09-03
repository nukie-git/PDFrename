"""logger.py (PDFrename v1.4.0)

Daily rotating logger module. Manages the logs/ directory, writes daily log files (logs/YYYYMMDD.log),
and automatically prunes old log files beyond the 7 most recent days.
"""

import os
import glob
from datetime import datetime

def get_logs_dir():
    project_root = os.path.dirname(os.path.abspath(__file__))
    logs_dir = os.path.join(project_root, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir

def rotate_logs(logs_dir, max_keep=7):
    try:
        log_files = sorted(glob.glob(os.path.join(logs_dir, '*.log')))
        if len(log_files) > max_keep:
            to_remove = log_files[:-max_keep]
            for f in to_remove:
                try:
                    os.remove(f)
                except Exception:
                    pass
    except Exception:
        pass

def log(message, level='INFO'):
    try:
        logs_dir = get_logs_dir()
        rotate_logs(logs_dir, max_keep=7)
        
        today_str = datetime.now().strftime('%Y%m%d')
        log_path = os.path.join(logs_dir, f'{today_str}.log')
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f'[{timestamp}] [{level}] {message}\n'
        
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(log_line)
    except Exception as e:
        print(f'[LOG WARNING] Failed to write log: {e}')
