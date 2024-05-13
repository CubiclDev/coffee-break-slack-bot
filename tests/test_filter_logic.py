import random
import pytest

from contextlib import nullcontext as does_not_raise
from freezegun import freeze_time

# Assuming the filter_users_based_on_previous_runs function is in the 'main' module
from slack_bot.app import filter_users_based_on_previous_runs, generate_user_pairs


@freeze_time("2023-08-01")
def test_filter_users_choose_users_without_history():
    # given
    sample_runs = [
        {'date': '2023-07-02', 'pair': ['user5', 'user6']},
        {'date': '2023-07-02', 'pair': ['user7', 'user8']},
        {'date': '2023-07-02', 'pair': ['user9', 'user1']},
    ]
    users = [f"user{i}" for i in range(1, 10)]

    # when
    taking_break = filter_users_based_on_previous_runs(users, sample_runs)

    # then
    # haven't had a run within the last 30 days
    assert len(taking_break) == 6
    assert "user2" in taking_break
    assert "user3" in taking_break
    assert "user4" in taking_break


def test_filter_users_correct_number_without_history():
    # given
    users = [f"user{i}" for i in range(1, 10)]

    # when
    taking_break = filter_users_based_on_previous_runs(users, [])

    # then
    assert len(taking_break) == 6


def test_filter_users_correct_number_with_all_have_history():
    # given
    sample_runs = [
        {'date': '2023-07-02', 'pair': ['user1', 'user2']},
        {'date': '2023-07-02', 'pair': ['user3', 'user4']},
        {'date': '2023-07-02', 'pair': ['user5', 'user6']},
        {'date': '2023-07-02', 'pair': ['user7', 'user8']},
        {'date': '2023-07-02', 'pair': ['user9', 'user1']},
    ]
    users = [f"user{i}" for i in range(1, 10)]

    # when
    taking_break = filter_users_based_on_previous_runs(users, [])

    # then
    assert len(taking_break) == 6


@pytest.mark.parametrize(
    "users,expected_user_pairs",
    [
        [
            ["a", "b", "c", "d"],
            [("a", "b"), ("c", "d")],
        ],
        [
            ["a", "d", "c", "b"],
            [("a", "d"), ("b", "c")],
        ],
        [
            ["a", "b", "c", "d", "e"],
            [("a", "b"), ("c", "d")],
        ],
    ],
)
def test_generate_user_pairs(users, expected_user_pairs):
    user_pairs = generate_user_pairs(users)
    assert user_pairs == expected_user_pairs


@pytest.mark.parametrize(
    "users,previous_runs,expected_raises,expected_filtered_users",
    [
        # Simplest cases, no previous runs and number of uses is a multiple of
        # 2, the filtered users should be 50% of the total users
        [
            ["a", "b"],
            [],
            does_not_raise(),
            ["a", "b"],
        ],
        [
            ["a", "b", "c", "d"],
            [],
            does_not_raise(),
            ["c", "a"],
        ],
        [
            ["a", "b", "c", "d", "e", "f", "g", "h"],
            [],
            does_not_raise(),
            ["e", "f", "b", "c"],
        ],
        # A few cases for even numbers of users
        [
            ["a", "b", "c", "d", "e", "f"],
            [],
            does_not_raise(),
            ["e", "b", "c", "a"],
        ],
        [
            ["a", "b", "c", "d", "e", "f", "g",  "h", "i", "j"],
            [],
            does_not_raise(),
            ["f", "h", "e", "i", "d", "b"],
        ],
        # A few cases for odd numbers of users
        [
            ["a", "b", "c"],
            [],
            does_not_raise(),
            ["c", "a"],
        ],
        [
            ["a", "b", "c", "d", "e"],
            [],
            does_not_raise(),
            ["c", "a", "b", "e"],
        ],
        [
            ["a", "b", "c", "d", "e", "f", "g", "h", "i"],
            [],
            does_not_raise(),
            ["c", "h", "e", "f", "b", "d"],
        ],
        [
            ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k"],
            [],
            does_not_raise(),
            ["b", "i", "c", "d", "j", "f"],
        ],
        # Some users have been chosen last time, pairs should only be created
        # from new users
        [
            ["a", "b", "c", "d", "e", "f", "g", "h"],
            [
                {"date": "2023-07-02", "pair": ["a", "b"]},
                {"date": "2023-07-02", "pair": ["c", "d"]},
            ],
            does_not_raise(),
            ["g", "e", "h", "f"],
        ],
        # "b" is the only needed user, "a", "c" and "e" are filled randomly to
        # reach 50%. The only valid pair for "a" is (a, b) and therefore the
        # other pair is (c, e).
        [
            ["a", "b", "c", "d", "e"],
            [
                {"date": "2023-07-02", "pair": ["a", "c"]},
                {"date": "2023-07-02", "pair": ["a", "e"]},
                {"date": "2023-07-02", "pair": ["c", "d"]},
            ],
            does_not_raise(),
            ["b", "a", "e", "c"],
        ],
        # No valid pair, as only (a, b) is possible but was used last time
        [
            ["a", "b"],
            [
                {"date": "2023-07-02", "pair": ["a", "b"]},
            ],
            pytest.raises(ValueError),
            [],
        ],
        # Gets stuck in a loop shuffling (b, c), valid would be (a, c). This is
        # the result of all users being present in the list of previous runs,
        # which is a valid edge case, but not relevant given that we only
        # select pairs for 50% of the users every time.
        [
            ["a", "b", "c"],
            [
                {"date": "2023-07-02", "pair": ["a", "b"]},
                {"date": "2023-07-02", "pair": ["b", "c"]},
            ],
            pytest.raises(ValueError),
            [],
        ],
    ],
)
def test_filter_users_based_on_previous_runs_no_duplicates(
    users,
    previous_runs,
    expected_raises,
    expected_filtered_users
):
    random.seed(0)
    with expected_raises:
        filtered_users = filter_users_based_on_previous_runs(users, previous_runs)
        assert filtered_users == expected_filtered_users
