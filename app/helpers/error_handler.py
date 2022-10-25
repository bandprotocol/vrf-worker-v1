import requests
from typing import Type
from .config import AppEnvConfig
from .database import Database


class ErrorHandler:
    def __init__(self, _config: Type[AppEnvConfig]) -> None:
        self.config = _config

    def check_error_limit(self, error_count: int) -> None:
        """Checks the error count.

        Sends notification to discord if the error count reaches 3.

        Args:
            error_count (int): Cumulative error count
        """
        try:
            if error_count == 3:
                message = f"<{self.config.CHAIN}> VRF Worker failed to run multiple times!"
                ErrorHandler.send_notification_to_discord(self.config.DISCORD_WEBHOOK, message)

        except Exception as e:
            print("Error check_error_count", e)

    @staticmethod
    def send_notification_to_discord(url: str, message: str) -> None:
        """Sends notification to discord.

        Args:
            url (str): Discord webhook URL.
            message (str): Message to send.
        """
        try:
            res = requests.post(
                url=url,
                json={"content": message},
                headers={"Content-type": "application/json"},
            )

            res.raise_for_status()

        except Exception as e:
            print("Error send_notification_to_discord", e)
            raise

    @staticmethod
    def current_error_count(db: Database) -> None:
        """Retrieves the current error count from database

        Args:
            db (Database): Database object for interacting with the SQL database.
        """
        try:
            return db.get_error_count()

        except Exception as e:
            print("Error check_error_count", e)
            raise

    @staticmethod
    def update_error_count(db: Database, new_count: int) -> None:
        """Update the error count in the database

        Args:
            db (Database): Database object for interacting with the SQL database.
            new_count (int): New error count
        """
        try:
            db.change_error_count(new_count)
            db.session.commit()

        except Exception as e:
            db.session.rollback()
            print("Error update_error_count", e)
            raise
