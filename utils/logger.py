import logging


class CustomFormatter(logging.Formatter):
    """Logging Formatter that adds colours"""

    grey = "\x1b[38;21m"
    green = "\x1b[32;40m"
    yellow = "\x1b[33;21m"
    red = "\x1b[31;21m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    _format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: grey + _format + reset,
        logging.INFO: green + _format + reset,
        logging.WARNING: yellow + _format + reset,
        logging.ERROR: red + _format + reset,
        logging.CRITICAL: bold_red + _format + reset
    }

    def format(self, record: logging.LogRecord) -> str:
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def create_logger(name: str, severity) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(severity)

    ch = logging.StreamHandler()
    ch.setLevel(severity)
    ch.setFormatter(CustomFormatter())

    logger.addHandler(ch)

    return logger
