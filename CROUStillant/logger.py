import os
import logging
import logging.handlers


class Logger:
    """
    La classe Logger permet de gérer les logs de l'application.
    """
    def __init__(self, file: str) -> None:
        """
        Initialisation du logger
        """
        self.file = file
        
        path = os.path.join(f"{os.getcwd()}", 'logs')
        if not os.path.exists(path):
            os.makedirs(path)

        self.logger = logging.getLogger(f"CROUStillant - {self.file}")
        self.logger.setLevel(logging.DEBUG)

        handler = logging.handlers.RotatingFileHandler(
            filename=f"{path}/{self.file}.log",
            encoding='utf-8',
            maxBytes=32 * 1024 * 1024,
            backupCount=5,
        )
        dt_fmt = '%Y-%m-%d %H:%M:%S'
        formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        self.logger.info("Logger initialisé !")


    def info(self, message: str) -> None:
        """
        Inscrire un message d'information
        
        :param message: The message
        """
        self.logger.info(message)

    
    def warning(self, message: str) -> None:
        """
        Inscrire un message d'avertissement
        
        :param message: The message
        """
        self.logger.warning(message)

    
    def error(self, message: str) -> None:
        """
        Inscrire un message d'erreur
        
        :param message: The message
        """
        self.logger.error(message)

    
    def critical(self, message: str) -> None:
        """
        Inscrire un message critique
        
        :param message: The message
        """
        self.logger.critical(message)

    
    def debug(self, message: str) -> None:
        """
        Inscrire un message de débogage
        
        :param message: The message
        """
        self.logger.debug(message)
