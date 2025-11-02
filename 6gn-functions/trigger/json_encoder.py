import json
from bson import ObjectId
from datetime import datetime

# keep recent_trajectories as a list and only encode the created_at and _id fields in each dictionary
class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(v, ObjectId) or isinstance(v, datetime):
                    o[k] = self.default(v)
            return o
        elif isinstance(o, ObjectId):
            return str(o)
        elif isinstance(o, datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)