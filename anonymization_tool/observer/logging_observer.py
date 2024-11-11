# anonymization_tool/logging_observer.py

from .observer import Observer
import os
from datetime import datetime

class LoggingObserver(Observer):
    def __init__(self, log_folder):
        self.log_folder = log_folder

    def update(self, event, data):
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        log_filename = f'log_{timestamp}.txt'
        log_path = os.path.join(self.log_folder, log_filename)

        with open(log_path, 'a') as log_file:
            log_file.write(f"{timestamp} - {event}: {data}\n")