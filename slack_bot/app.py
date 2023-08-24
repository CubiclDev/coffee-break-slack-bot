import datetime
import json
import logging
import math
import os
import random
import boto3
from typing import List, Tuple
from abc import ABC, abstractmethod

from slack_sdk import WebClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)
ABSENCE_EMOJIS = [":palm_tree:", ":face_with_thermometer:"]

class FileHandler(ABC):
    @abstractmethod
    def read(self) -> List[dict]:
        pass

    @abstractmethod
    def write(self, data: List[dict]) -> None:
        pass


class S3FileHandler(FileHandler):
    def __init__(self, bucket: str, key: str):
        self.s3 = boto3.client('s3', aws_access_key_id=os.environ['AWS_ACCESS_KEY'], aws_secret_access_key=os.environ['AWS_SECRET_KEY'])
        self.bucket = bucket
        self.key = key

    def read(self) -> List[dict]:
        try:
            self.s3.download_file(self.bucket, self.key, '/tmp/runs.jsonl')
            with open('/tmp/runs.jsonl', 'r') as f:
                return [json.loads(line) for line in f]
        except Exception as e:
            logger.warning(f"Error downloading file from S3: {e}")
            return []

    def write(self, data: List[dict]) -> None:
        try:
            with open('/tmp/runs.jsonl', 'a') as f:
                for entry in data:
                    f.write(json.dumps(entry) + '\n')
            self.s3.upload_file('/tmp/runs.jsonl', self.bucket, self.key)
        except Exception as e:
            logger.warning(f"Error uploading file to S3: {e}")


class LocalFileHandler(FileHandler):
    def __init__(self, key: str):
        self.key = key

    def read(self) -> List[dict]:
        try:
            with open(self.key, 'r') as f:
                return [json.loads(line) for line in f]
        except Exception as e:
            logger.warning(f"Error reading file from local filesystem: {e}")
            return []

    def write(self, data: List[dict]) -> None:
        try:
            with open(self.key, 'a') as f:
                for entry in data:
                    f.write(json.dumps(entry) + '\n')
        except Exception as e:
            logger.warning(f"Error writing file to local filesystem: {e}")


def handler(__event, __context) -> None:
    file_handler = S3FileHandler(os.environ['S3_BUCKET'], os.environ['S3_KEY'])
    process_users(file_handler)


def local_dev_handler(__event, __context) -> None:
    file_handler = LocalFileHandler('runs.jsonl')
    process_users(file_handler)


def process_users(file_handler: FileHandler) -> None:
    client = WebClient(token=get_token())
    users = get_users(client)

    # Load previous runs from file handler
    previous_runs = file_handler.read()

    # Filter users based on previous runs
    users = filter_users_based_on_previous_runs(users, previous_runs)

    # create pairs from entries
    logger.info("Picking from user list: %s", users)

    user_pairs = list(zip(users[::2], users[1::2]))
    logger.info("Picked pairs: %s", user_pairs)

    for user_pair in user_pairs:
        send_message(user_pair, client)

    # Update runs file
    file_handler.write([{"date": datetime.datetime.now().isoformat(), "pair": pair} for pair in user_pairs])


def send_message(users: list[str], client: WebClient) -> None:
    response = client.conversations_open(users=users)
    user_name_1 = get_user_name(users[0], client)
    user_name_2 = get_user_name(users[1], client)
    logger.info(f"Send coffee break message to {user_name_1} and {user_name_2}")

    client.chat_postMessage(
        channel=response["channel"]["id"],
        text=get_message(user_name_1, user_name_2)
    )


def get_message(user_name_1: str, user_name_2: str) -> str:
    language = os.environ.get("LANGUAGE", "en")

    if language == "de":
        return f"{user_name_1} und {user_name_2}, ihr wurdet für einen gemeinsamen Kaffeeklatsch ausgelost.\n" \
               "Bitte sucht euch für diese Woche einen Zeitslot von 15-20 Minuten.\n\n" \
               "Euer Kaffeebot ☕"

    # return english as default
    return f"{user_name_1} and {user_name_2}, you were selected for a shared coffee break.\n" \
           "Please schedule a meeting of 15-20 minutes this week.\n\n" \
           "Your coffee bot ☕"

def get_token() -> str:
    return os.environ["SLACK_TOKEN"]


def get_users(client: WebClient) -> list:
    users = json.loads(os.environ.get("USERS"))
    return filter_users(users, client)


def filter_users(users: list[str], client: WebClient) -> list[str]:
    filtered_users = filter(lambda user: is_included_user(user, client), users)
    return list(filtered_users)


def is_included_user(user: str, client: WebClient) -> bool:
    user_info = client.users_info(user=user)["user"]
    if user_info["deleted"]:
        return False
    if user_info["profile"]["status_emoji"] not in ABSENCE_EMOJIS:
        return True

    status_expiration = user_info["profile"]["status_expiration"]
    tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
    if status_expiration != 0 and status_expiration < tomorrow.timestamp():
        return True

    return False

def get_user_name(user_id: str, client: WebClient) -> str:
    user_info = client.users_info(user=user_id)
    user_name = user_info["user"]["profile"]["real_name"]
    return user_name.split()[0]

def filter_users_based_on_previous_runs(users, previous_runs):
    thirty_days_ago = datetime.datetime.now() - datetime.timedelta(days=30)

    # Find the last run date of each user
    last_run_dates = {}
    for run in previous_runs:
        for user in run['pair']:
            if user not in last_run_dates or datetime.datetime.fromisoformat(run['date']) > datetime.datetime.fromisoformat(last_run_dates[user]):
                last_run_dates[user] = run['date']

    # Users who need a break due to the 30-day rule
    need_break_users = {user for user in users if user not in last_run_dates or datetime.datetime.fromisoformat(last_run_dates[user]) < thirty_days_ago}

    # Users from the latest run date (those who took a break in the last round)
    latest_run_date = max(run['date'] for run in previous_runs) if previous_runs else "1970-01-01"
    last_round_users = {user for run in previous_runs if run['date'] == latest_run_date for user in run['pair']}

    # If we haven't met the 50% rule, add random users to fill incomplete user pairs
    available_users = list(set(users) - need_break_users - last_round_users)
    required_users_count = len(users) // 2 - len(need_break_users)
    if required_users_count > 0:
        need_break_users.update(random.sample(available_users, required_users_count))

    return list(need_break_users)
