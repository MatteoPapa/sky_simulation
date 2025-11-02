# 6gn Anti-collision ingester
supposed to subscribe to UAV updates and async call the update function on tinyfaas.
## Note
- Note you should update the kafka host address

### Description
- parse the UAV updates expected as following format:
```json
{
    "uav_id": "001",
    "uav_type": "1",
    "latitude": 52.0,
    "longitude": 0.1,
    "altitude": 10000,
    "speed": 50,
    "direction": 90,
    "vertical_speed": 0
}
```

- it will then make an array of data and a meta with origin = self_report and timestamp:
```json
{
  "data": [
      {
        "uav_id": "001",
        "uav_type": "1",
        "latitude": 52.0,
        "longitude": 0.1,
        "altitude": 10000,
        "speed": 50,
        "direction": 90,
        "vertical_speed": 0
    }
],
    "meta": {
        "origin": "self_report",
        "ingest_timestamp": "2021-06-01T13:00:00Z"
    }
}
```

Supposed to run on the same docker-compose file as kafka and db.

### Sample producer
there is a sample producer for this ingester in the producer folder that will send an uav message to the topic "uav_updates" every second.