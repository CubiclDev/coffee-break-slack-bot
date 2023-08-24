from freezegun import freeze_time

# Assuming the filter_users_based_on_previous_runs function is in the 'main' module
from slack_bot import filter_users_based_on_previous_runs

# Sample Data
users = [f"user{i}" for i in range(1, 21)]
sample_runs = [
    {'date': '2023-07-01', 'pair': ['user1', 'user2']},
    {'date': '2023-07-02', 'pair': ['user3', 'user4']},
    {'date': '2023-07-03', 'pair': ['user5', 'user6']},
    {'date': '2023-07-04', 'pair': ['user7', 'user8']},
    {'date': '2023-07-05', 'pair': ['user9', 'user10']},  
    # ... Repeated these 9 users having breaks so they have many occurrences
    {'date': '2023-07-30', 'pair': ['user1', 'user2']},
    {'date': '2023-07-31', 'pair': ['user3', 'user4']},
    # Some outliers and special cases
    {'date': '2023-07-31', 'pair': ['user11', 'user12']},
    {'date': '2023-07-31', 'pair': ['user13', 'user14']},
    {'date': '2023-07-31', 'pair': ['user15', 'user16']},
    {'date': '2023-07-31', 'pair': ['user17', 'user18']}
]

@freeze_time("2023-08-01")
def test_break_after_30_days():
    taking_break = filter_users_based_on_previous_runs(users, sample_runs)
    # user1 to user9 should definitely take a break, as they've been running a lot!
    for i in range(1, 10):
        assert f"user{i}" in taking_break

@freeze_time("2023-08-01")
def test_skip_a_round():
    taking_break = filter_users_based_on_previous_runs(users, sample_runs)
    # Users who took a break on '2023-07-31' should not take a break now (user3, user4, and users from user11 to user18)
    not_taking_break = {'user3', 'user4', 'user11', 'user12', 'user13', 'user14', 'user15', 'user16', 'user17', 'user18'}
    assert not any(user in taking_break for user in not_taking_break)

@freeze_time("2023-08-01")
def test_50_percent_rule():
    taking_break = filter_users_based_on_previous_runs(users, sample_runs)
    assert len(taking_break) == len(users) // 2  # Exactly 50% of the users should take a break
