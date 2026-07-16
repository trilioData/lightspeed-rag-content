import logging

# Custom formatter

logger = logging.getLogger("harness")
logger.setLevel(logging.INFO)

formatter = logging.Formatter(
    fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
# Console handler
console = logging.StreamHandler()
console.setFormatter(formatter)
logger.addHandler(console)

# # File handler
# file_handler = logging.FileHandler(f"logs/run-{run_id}.log")
# file_handler.setFormatter(formatter)
# logger.addHandler(file_handler)