import datetime
import json
import logging
import math
import os
import random

from slack_sdk import WebClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)
ABSENCE_EMOJIS = [":palm_tree:", ":face_with_thermometer:"]


def handler(__event, __context) -> None:
    client = WebClient(token=get_token())
    users = get_users(client)


    # shuffle the users array
    random.shuffle(users)

    # take half of the users (if it's odd, make it even, by using ceil)
    half_users = users[:math.ceil(len(users) / 2)]

    # create pairs from entries
    user_pairs = list(zip(half_users[::2], half_users[1::2]))
    for user_pair in user_pairs:
        send_message(user_pair, client)

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
