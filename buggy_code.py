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

print(divide_numbers(10, 0))
