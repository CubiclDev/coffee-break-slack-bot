from freezegun import freeze_time

# Assuming the filter_users_based_on_previous_runs function is in the 'main' module
from slack_bot.app import filter_users_based_on_previous_runs


@freeze_time("2023-08-01")
def test_filter_users():
    sample_runs = [
        {'date': '2023-07-02', 'pair': ['user5', 'user6']},
        {'date': '2023-07-02', 'pair': ['user7', 'user8']},
        {'date': '2023-07-02', 'pair': ['user9', 'user1']},
    ]
    users = [f"user{i}" for i in range(1, 10)]
    taking_break = filter_users_based_on_previous_runs(users, sample_runs)

    # haven't had a run within the last 30 days
    assert "user2" in taking_break
    assert "user3" in taking_break
    assert "user4" in taking_break
