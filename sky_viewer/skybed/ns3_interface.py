# skybed/ns3_interface.py
from pydantic import BaseModel

class NetworkParams(BaseModel):
    # Add fields if you need to emulate radio/network effects later
    latency_ms: float = 0.0
    downlink_mbps: float = 0.0
    uplink_mbps: float = 0.0
