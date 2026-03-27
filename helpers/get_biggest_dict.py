def count_keys_recursive(data):
    count = 0
    if isinstance(data, dict):
        count += len(data)
        for value in data.values():
            count += count_keys_recursive(value)
    elif isinstance(data, list):
        for item in data:
            count += count_keys_recursive(item)
    return count

def get_biggest_dict(dict_list):
    return max(dict_list, key=count_keys_recursive)