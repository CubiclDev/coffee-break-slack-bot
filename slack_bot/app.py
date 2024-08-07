import json
import logging
import os
import random
import math
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List

import boto3
from slack_sdk import WebClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)
ABSENCE_EMOJIS = [":palm_tree:", ":face_with_thermometer:", ":baby:"]


class FileHandler(ABC):
    @abstractmethod
    def read(self) -> List[dict]:
        pass

    @abstractmethod
    def write(self, data: List[dict]) -> None:
        pass


class S3FileHandler(FileHandler):
    def __init__(self, bucket: str, prefix: str):
        self.s3 = boto3.client("s3")
        self.bucket = bucket
        self.prefix = prefix

    def _get_object_key(self):
        current_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return f"{self.prefix}/{current_date}.json"

    def read(self) -> List[dict]:
        try:
            object_list = self.s3.list_objects_v2(Bucket=self.bucket, Prefix=self.prefix)
            file_keys = [obj["Key"] for obj in object_list.get("Contents", [])]

            all_data = []
            for file_key in sorted(file_keys):
                response = self.s3.get_object(Bucket=self.bucket, Key=file_key)
                data = response["Body"].read().decode("utf-8")
                data_list = json.loads(data)
                all_data.extend(data_list)

            return all_data
        except Exception as e:
            logger.warning(f"Error reading data from S3: {e}")
            return []

    def write(self, data: List[dict]) -> None:
        try:
            self.s3.put_object(
                Bucket=self.bucket,
                Key=self._get_object_key(),
                Body=json.dumps(data),
            )
        except Exception as e:
            logger.warning(f"Error writing data to S3: {e}")


def handler(__event, __context) -> None:
    file_handler = S3FileHandler(os.environ["S3_BUCKET"], os.environ["S3_PREFIX"])
    process_users(file_handler)


def generate_user_pairs(users: list[str]) -> list[tuple[str]]:
    user_pairs = list(zip(users[::2], users[1::2]))
    return [tuple(sorted(pair)) for pair in user_pairs]


def process_users(file_handler: FileHandler) -> None:
    client = WebClient(token=get_token())
    users = get_users(client)

    # Load previous runs from file handler
    previous_runs = file_handler.read()

    # Filter users based on previous runs
    filtered_users = filter_users_based_on_previous_runs(users, previous_runs)

    user_pairs = generate_user_pairs(filtered_users)

    for user_pair in user_pairs:
        send_message(list(user_pair), client)

    # Update runs file
    file_handler.write([{"date": datetime.now().date().isoformat(), "pair": pair} for pair in user_pairs])


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
    users = list(json.loads(os.environ.get("USERS")).values())
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
    tomorrow = datetime.now() + timedelta(days=1)
    if status_expiration != 0 and status_expiration < tomorrow.timestamp():
        return True

    return False


def get_user_name(user_id: str, client: WebClient) -> str:
    user_info = client.users_info(user=user_id)
    user_name = user_info["user"]["profile"]["real_name"]
    return user_name.split()[0]


def filter_users_based_on_previous_runs(users, previous_runs) -> list[str]:
    if len(users) < 2:
        return []

    # Find the last run date of each user
    last_run_dates = {user: max(run["date"] for run in previous_runs if user in run["pair"]) for user in users if
                      any(user in run["pair"] for run in previous_runs)}

    # Users who need a coffee break as they had none in the last 30 days
    need_break_users = [user for user in users if user not in last_run_dates]
    random.shuffle(need_break_users)
    other_users = [user for user in users if user not in need_break_users]

    # Users from the latest run date (those who took a break in the last round)
    latest_run_date = max(run["date"] for run in previous_runs) if previous_runs else "1970-01-01"
    last_run_pairs = [tuple(sorted(pair)) for pair in
                      [run['pair'] for run in previous_runs if run['date'] == latest_run_date]]

    # If we haven't met the 50% rule, add random users to fill incomplete user pairs
    number_of_coffee_break_users = math.ceil(len(users) / 4) * 2
    required_users_count = number_of_coffee_break_users - len(need_break_users)

    coffee_break_users = need_break_users
    if required_users_count < 0:
        del coffee_break_users[required_users_count:]
    elif required_users_count > 0:
        coffee_break_users.extend(random.sample(other_users, required_users_count))

    # Keep shuffling until a suitable arrangement (no combination from last run) is found
    random.shuffle(coffee_break_users)
    user_pairs = generate_user_pairs(coffee_break_users)
    num_tries = 0
    max_tries = 1000
    while any(pair in last_run_pairs for pair in user_pairs):
        random.shuffle(coffee_break_users)
        user_pairs = generate_user_pairs(coffee_break_users)
        num_tries += 1
        print(coffee_break_users)
        if num_tries > max_tries:
            raise ValueError("Given users and previous runs do not produce valid pairs.")

    return coffee_break_users
