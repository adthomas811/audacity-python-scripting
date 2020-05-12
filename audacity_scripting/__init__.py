
from datetime import datetime
import logging
from os import mkdir
from os.path import abspath, dirname, isdir, isfile, join
from time import sleep

package_path = dirname(abspath(__file__))
log_dir_path = join(package_path, '_logs')
LOGGER_NAME = __name__

if not isdir(log_dir_path):
    mkdir(log_dir_path)

current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_file = join(log_dir_path, current_time + '.log')

if isfile(log_file):
    sleep(1)
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = join(log_dir_path, current_time + '.log')

# Create the Logger
logger = logging.getLogger(LOGGER_NAME)
logger.setLevel(logging.DEBUG)

# Create the Handler for logging data to a file
logger_handler = logging.FileHandler(log_file)
logger_handler.setLevel(logging.DEBUG)

# Create a Formatter for formatting the log messages
logger_formatter = logging.Formatter('%(asctime)s - %(levelname)-8s - '
                                     '%(message)s')

# Add the Formatter to the Handler
logger_handler.setFormatter(logger_formatter)

# Add the Handler to the Logger
logger.addHandler(logger_handler)
