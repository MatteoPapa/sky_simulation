from pymongo import MongoClient
from datetime import datetime

# Create a MongoClient to the running MongoDB instance
host = "172.17.0.1"  # TODO use ENV variables
client = MongoClient(f'mongodb://{host}:27017/')

# Access the 'trajectories' collection in the 'sixGNext' database
db = client.sixGNext
trajectories = db.trajectories

def store_update(data):
    # Add a 'created_at' key to all 'data' elements with the current timestamp
    created_time = datetime.now()
    for element in data:
        element['created_at'] = created_time
        # in case of mutated release, let mongo generate the _id and not a duplicate of original id
        element.pop('_id', None)

    # Insert all elements of the data into the 'trajectories' collection at once
    trajectories.insert_many(data)
    # for element in data:
    #     trajectories.insert_one(element)