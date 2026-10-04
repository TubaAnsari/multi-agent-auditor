
import pytest

def divide_numbers(a, b):
    return a / b

def get_user_data(user_id):
    data = fetch_from_db(user_id)
    return data

def process_list(items):
    total = 0
    for i in range(len(items)):
        total = total + items[i]
    return total

# Mock function to simulate database fetch
def fetch_from_db(user_id):
    # Simulate fetching data from a database
    if user_id == "123":
        return {"name": "John", "age": 30}
    else:
        raise ValueError("User not found")

@pytest.fixture
def mock_fetch_from_db(monkeypatch):
    def mock_function(user_id):
        return fetch_from_db(user_id)
    monkeypatch.setattr('fetch_from_db', mock_function)

# Test divide_numbers with normal use case
def test_divide_numbers_normal():
    assert divide_numbers(10, 2) == 5

# Test divide_numbers with edge case (zero divisor)
def test_divide_numbers_zero_divisor():
    with pytest.raises(ZeroDivisionError):
        divide_numbers(10, 0)

# Test get_user_data with normal use case
def test_get_user_data_normal(mock_fetch_from_db):
    assert get_user_data("123") == {"name": "John", "age": 30}

# Test get_user_data with edge case (user not found)
def test_get_user_data_user_not_found(mock_fetch_from_db):
    with pytest.raises(ValueError):
        get_user_data("456")

# Test process_list with normal use case
def test_process_list_normal():
    assert process_list([1, 2, 3, 4]) == 10

# Test process_list with edge case (empty list)
def test_process_list_empty_list():
    assert process_list([]) == 0
