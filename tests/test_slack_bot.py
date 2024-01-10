import copy
import json
import os

import pytest
from freezegun import freeze_time
from moto import mock_s3
import boto3

from slack_bot import __version__
from slack_bot.app import (
    get_message,
    is_included_user,
    handler,
    send_message,
)
from slack_bot.app import S3FileHandler
from slack_sdk import WebClient

TEST_USERS = [
    "U1",
    "U2",
    "U3",
    "U4",
    "U5",
    "U6",
    "U7",
    "U8",
    "U9",
]


def test_version():
    assert __version__ == "0.1.0"


@freeze_time("2021-01-02")
def test_handler(mocker):
    os.environ['S3_BUCKET'] = 'cubicl-bot'
    os.environ['S3_PREFIX'] = 'runs'
    # given
    mock_get_all_users = mocker.patch(
        "slack_bot.app.get_users", return_value=copy.deepcopy(TEST_USERS)
    )
    mock_token = mocker.patch("slack_bot.app.get_token", return_value="xxx")
    mock_send_message = mocker.patch("slack_bot.app.send_message")
    mock_file_handler_read = mocker.patch("slack_bot.app.S3FileHandler.read", return_value=[])
    mock_file_handler_write = mocker.patch("slack_bot.app.S3FileHandler.write")

    # when
    handler("", "")

    # then
    mock_get_all_users.assert_called_once()
    mock_token.assert_called_once()
    mock_file_handler_read.assert_called_once()
    mock_file_handler_write.assert_called_once()
    assert mock_send_message.call_count == 3


def test_send_message(mocker):
    # given
    mock_conversations_open = mocker.patch(
        "slack_sdk.WebClient.conversations_open",
        return_value={"channel": {"id": "dummy"}},
    )
    mock_chat_postMessage = mocker.patch("slack_sdk.WebClient.chat_postMessage")
    mock_get_user_name = mocker.patch(
        "slack_bot.app.get_user_name", side_effect=["Name1", "Name2"]
    )

    # when
    send_message(["U1", "U2"], client=WebClient())

    # then
    mock_conversations_open.assert_called_once()
    mock_chat_postMessage.assert_called_once()
    assert mock_get_user_name.call_count == 2
    assert mock_get_user_name.call_args_list[0].args[0] == "U1"
    assert mock_get_user_name.call_args_list[1].args[0] == "U2"
    assert (
            mock_chat_postMessage.call_args_list[0][1]["text"]
            == "Name1 and Name2, you were selected for a shared coffee break.\n"
               "Please schedule a meeting of 15-20 minutes this week.\n\n"
               "Your coffee bot ☕"
    )


@pytest.mark.parametrize(
    "language,expected_message",
    [
        (
                None,
                "Name1 and Name2, you were selected for a shared coffee break.\n"
                "Please schedule a meeting of 15-20 minutes this week.\n\n"
                "Your coffee bot ☕",
        ),
        (
                "en",
                "Name1 and Name2, you were selected for a shared coffee break.\n"
                "Please schedule a meeting of 15-20 minutes this week.\n\n"
                "Your coffee bot ☕",
        ),
        (
                "not_defined_language",
                "Name1 and Name2, you were selected for a shared coffee break.\n"
                "Please schedule a meeting of 15-20 minutes this week.\n\n"
                "Your coffee bot ☕",
        ),
        (
                "de",
                "Name1 und Name2, ihr wurdet für einen gemeinsamen Kaffeeklatsch ausgelost.\n"
                "Bitte sucht euch für diese Woche einen Zeitslot von 15-20 Minuten.\n\n"
                "Euer Kaffeebot ☕",
        ),
    ],
)
def test_get_message(mocker, language: str, expected_message: str):
    # given
    if language:
        mocker.patch.dict(os.environ, {"LANGUAGE": language}, clear=True)

    # when
    message = get_message("Name1", "Name2")

    # then
    assert message == expected_message


@pytest.mark.parametrize(
    "user,user_info,expected_value",
    [
        (
                "DELETED_USER_ID",
                {
                    "user": {
                        "deleted": True,
                        "profile": {"status_emoji": "", "status_expiration": 0},
                    }
                },
                False,
        ),
        (
                "HOLIDAY_USER_ID",
                {
                    "user": {
                        "deleted": False,
                        "profile": {"status_emoji": ":palm_tree:", "status_expiration": 0},
                    }
                },
                False,
        ),
        (
                "HOLIDAY_EXPIRES_EARLY_USER_ID",
                {
                    "user": {
                        "deleted": False,
                        "profile": {
                            "status_emoji": ":palm_tree:",
                            "status_expiration": 1662793200,
                        },
                    }
                },
                True,
        ),
        (
                "HOLIDAY_EXPIRES_LATE_USER_ID",
                {
                    "user": {
                        "deleted": False,
                        "profile": {
                            "status_emoji": ":palm_tree:",
                            "status_expiration": 1662879600,
                        },
                    }
                },
                False,
        ),
        (
                "ILL_USER_ID",
                {
                    "user": {
                        "deleted": False,
                        "profile": {
                            "status_emoji": ":face_with_thermometer:",
                            "status_expiration": 0,
                        },
                    }
                },
                False,
        ),
        (
                "STANDARD_USER_ID",
                {
                    "user": {
                        "deleted": False,
                        "profile": {"status_emoji": "", "status_expiration": 0},
                    }
                },
                True,
        ),
        (
                "STANDARD_USER_ID_WITH_EMOJI",
                {
                    "user": {
                        "deleted": False,
                        "profile": {"status_emoji": ":no_entry:", "status_expiration": 0},
                    }
                },
                True,
        ),
    ],
)
@freeze_time("2022-09-09 10:00:00")
def test_is_included_user(mocker, user: str, user_info: dict, expected_value: bool):
    # given
    mocker.patch("slack_sdk.WebClient.users_info", return_value=user_info)

    # when
    is_included = is_included_user(user, client=WebClient())

    # then
    assert is_included is expected_value


@mock_s3
def test_read_from_s3():
    # given
    os.environ['S3_BUCKET'] = 'cubicl-bot'
    os.environ['S3_PREFIX'] = 'runs'
    with mock_s3():
        bucket = 'test-bucket'
        s3_client = boto3.client('s3', region_name='us-east-1')
        s3_client.create_bucket(Bucket=bucket)
        sample_run = [
            {'date': '2023-07-02', 'pair': ['user5', 'user6']},
            {'date': '2023-07-02', 'pair': ['user7', 'user8']},
            {'date': '2023-07-02', 'pair': ['user9', 'user1']},
        ]
        s3_client.put_object(Body=json.dumps(sample_run), Bucket=bucket, Key="runs/test.jsonl")
        file_handler = S3FileHandler(bucket=bucket, prefix="runs")
        result = file_handler.read()
        assert result == sample_run