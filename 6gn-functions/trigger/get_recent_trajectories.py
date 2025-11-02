from pymongo import MongoClient
from datetime import datetime, timedelta


def get_recent_trajectories(seconds_ago):
    # Create a MongoClient to the running MongoDB instance
    host = "172.17.0.1"  # TODO use ENV variables
    client = MongoClient(f'mongodb://{host}:27017/')

    # Access the 'trajectories' collection in the 'sixGNext' database
    db = client.sixGNext
    trajectories = db.trajectories

    # Get the current time and calculate the time ttl seconds ago
    now = datetime.now()
    ttl = now - timedelta(seconds=seconds_ago)

    # Query the 'trajectories' collection for documents where 'created_at' is not older than ttl seconds
    recent_trajectories = trajectories.find({'created_at': {'$gte': ttl}})

    # Create a dictionary to store the most recent trajectory of each 'uav_id'
    recent_uav_trajectories = {}

    # Iterate over the recent trajectories
    for trajectory in recent_trajectories:
        uav_id = trajectory['uav_id']

        # If the 'uav_id' is not in the dictionary or the current trajectory is more recent, update the dictionary
        if uav_id not in recent_uav_trajectories or trajectory['created_at'] > recent_uav_trajectories[uav_id][
            'created_at']:
            recent_uav_trajectories[uav_id] = trajectory

    # Return the most recent trajectories of each 'uav_id'
    return list(recent_uav_trajectories.values())
