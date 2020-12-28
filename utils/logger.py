import logging


def create_logger(name: str, severity) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(severity)

    ch = logging.StreamHandler()
    ch.setLevel(severity)

    formatter = logging.Formatter("%(asctime)s — %(name)s — %(levelname)s — %(funcName)s:%(lineno)d — %(message)s")
    ch.setFormatter(formatter)

    logger.addHandler(ch)

    return logger