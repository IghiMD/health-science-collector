import logging

def setup_logger():
    logger = logging.getLogger("NjuzBot")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    ))
    logger.addHandler(handler)
    return logger

logger = setup_logger()
