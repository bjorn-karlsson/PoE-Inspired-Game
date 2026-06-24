import json
import random

# Parse the JSON data into a Python dictionary
json_data = '''
{
    "spawn_weights": [
        {
            "tag": "ring",
            "weight": 100
        },
        {
            "tag": "amulet",
            "weight": 1000
        },
        {
            "tag": "belt",
            "weight": 1000
        },
        {
            "tag": "str_armour",
            "weight": 1000
        },
        {
            "tag": "str_dex_armour",
            "weight": 1000
        },
        {
            "tag": "str_int_armour",
            "weight": 1000
        },
        {
            "tag": "str_dex_int_armour",
            "weight": 1000
        },
        {
            "tag": "sword",
            "weight": 1000
        },
        {
            "tag": "mace",
            "weight": 1000
        },
        {
            "tag": "sceptre",
            "weight": 1000
        },
        {
            "tag": "staff",
            "weight": 1000
        },
        {
            "tag": "axe",
            "weight": 1000
        },
        {
            "tag": "default",
            "weight": 0
        }
    ]
}
'''

data = json.loads(json_data)

# Create a dictionary of weights for each item
weights = {item['tag']: item['weight'] for item in data['spawn_weights']}

# Define a function to randomly choose an item based on its weight
def choose_item(weights):
    # Get the total weight of all items
    total_weight = sum(weights.values())
    # Generate a random number between 0 and the total weight
    random_num = random.uniform(0, total_weight)
    # Iterate over the items and their weights, subtracting each weight from the random number until it becomes negative
    for item, weight in weights.items():
        if random_num - weight < 0:
            return item
        random_num -= weight

# Call the function to choose an item

while True:
    chosen_item = choose_item(weights)
    print(chosen_item)
    if chosen_item == 'ring':
        break

