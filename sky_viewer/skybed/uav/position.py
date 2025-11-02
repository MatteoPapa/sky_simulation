import geopy.distance
from skybed.message_types import UAV

uav: UAV 

def update_position_from_trajectory(virtual_seconds_since_last_update: float):
    dt = float(virtual_seconds_since_last_update)
    if dt <= 0:
        return

    # quota: integra col vertical_speed
    new_altitude = uav.altitude + uav.vertical_speed * dt

    # orizzontale: distanza = speed[m/s]*dt -> km, geodesic con bearing in gradi
    d_km = (uav.speed * dt) / 1000.0
    if d_km > 0:
        uav.position = geopy.distance.geodesic(kilometers=d_km).destination(
            point=uav.position,
            bearing=uav.direction
        )

    uav.position.altitude = new_altitude
    uav.altitude = new_altitude

def update_trajectory_from_collision_avoidance_msg(new_uav: UAV):
    """
    Semplificata: applichiamo direttamente i comandi del release.
    NON tocchiamo lat/lon del messaggio: la posizione locale resta autoritativa.
    """
    if new_uav.speed is not None:
        uav.speed = float(new_uav.speed)
    if new_uav.direction is not None:
        uav.direction = float(new_uav.direction) % 360.0
    if new_uav.vertical_speed is not None:
        uav.vertical_speed = float(new_uav.vertical_speed)
    if new_uav.altitude is not None:
        uav.altitude = float(new_uav.altitude)
        try:
            uav.position.altitude = uav.altitude
        except Exception:
            pass
