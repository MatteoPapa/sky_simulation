# skybed/message_types.py
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict, PrivateAttr
from geopy import Point as GeoPoint

class UAV(BaseModel):
    # allow non-pydantic types in private attrs (geopy.Point)
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # --- JSON / public fields ---
    uav_id: str
    uav_type: str

    latitude: float
    longitude: float
    altitude: float = 0.0

    speed: float = 0.0           # m/s
    direction: float = 0.0       # deg (0=north, 90=east)
    vertical_speed: float = 0.0  # m/s

    # --- Private (non-serialized) geodesic point ---
    _position: Optional[GeoPoint] = PrivateAttr(default=None)

    # Keep the public API the same: uav.position <-> _position
    @property
    def position(self) -> Optional[GeoPoint]:
        return self._position

    @position.setter
    def position(self, pt: Optional[GeoPoint]) -> None:
        self._position = pt

    def model_post_init(self, __context) -> None:
        # initialize geopy point from scalars
        self._position = GeoPoint(self.latitude, self.longitude, self.altitude)

    def sync_from_point(self) -> None:
        """Copy lat/lon/alt from the internal geopy.Point to the public fields."""
        if self._position is None:
            return
        self.latitude = float(self._position.latitude)
        self.longitude = float(self._position.longitude)
        try:
            self.altitude = float(self._position.altitude or self.altitude)
        except Exception:
            pass

    def set_point(self, pt: GeoPoint) -> None:
        """Set the internal point and update the public fields in one call."""
        self._position = pt
        self.sync_from_point()
