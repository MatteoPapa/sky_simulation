import json
from bson import ObjectId
from datetime import datetime

# ObjectId type from MongoDB is not JSON serializable by default
# Also, datetime python object is not JSON serializable
class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        elif isinstance(o, datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)