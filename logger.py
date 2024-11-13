import queue
import logging
from logging.handlers import QueueHandler, QueueListener

class LogFormatter(logging.Formatter):
    def format(self, record):
        record.funcName = record.funcName.upper()
        record.top = record.top.upper()
        return logging.Formatter.format(self, record)

formatter = LogFormatter(
    "[%(asctime)s] [%(top)s] [%(funcName)s] [%(levelname)s] %(message)s"
)

def setup_logger(name, log_out, top, level=logging.INFO):
    extra=dict(top=top)

    if type(log_out) == str:
        handler = logging.FileHandler(log_out)        
    else:
        handler = logging.StreamHandler(log_out)

    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    logger = logging.LoggerAdapter(logger, extra)

    return logger

"""    log_queue = queue.Queue()
    queue_handler = QueueHandler(log_queue)

    root = logging.getLogger(name)
    root.setLevel(level)
    root.addHandler(queue_handler)
    root = logging.LoggerAdapter(root, extra)

    queue_listener = QueueListener(log_queue, handler)
    queue_listener.start()

    return root #logger"""
