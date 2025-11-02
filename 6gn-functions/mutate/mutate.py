import logging
import random

logger = logging.getLogger(__name__)


# decreases the speed of the lower priority UAV with a collision (from two colliding UAVs)
def dec_speed_of_lower_collider(trajectories, abilities):
    # Filter trajectories with collision set to True
    collision_trajectories = [t for t in trajectories if t.get('collision', False)]

    if len(collision_trajectories) <= 1:
        logger.error(
            f'[mutate fn] (case1) Not enough collisions to determine lower priority UAV: {collision_trajectories}')
        return False, f'(case1) Not enough collisions to determine lower priority UAV: {collision_trajectories}'

    # Find the trajectory with the highest uav_id (Lower priority)
    lowest_uav_id_trajectory = max(collision_trajectories, key=lambda t: t['uav_id'])  #TODO proper priority check

    # Decrease the speed by 25% (inplace)
    original_speed = lowest_uav_id_trajectory['speed']
    lowest_uav_id_trajectory['speed'] = original_speed * 0.75

    # set flags
    lowest_uav_id_trajectory['origin'] = 'mutate'  # flag the updated trajectory
    lowest_uav_id_trajectory['mutation_cases'] = f"{int(lowest_uav_id_trajectory.get('mutation_cases', '000'), 2) | 0b001:03b}"  # binary flag for Case 1. supposed to be null

    # Remove the "collision" key from each trajectory in collision_trajectories
    for trajectory in collision_trajectories:
        if 'collision' in trajectory:
            del trajectory['collision']

    logger.info(
        f"[mutate fn] Decreased speed of UAV {lowest_uav_id_trajectory['uav_id']} from {original_speed} to {lowest_uav_id_trajectory['speed']}")

    return True, trajectories


# changes the direction of the lower priority UAV with a collision (from two colliding UAVs)
def change_dir_of_lower_collider(trajectories,
                                 abilities):  # some functionalities are work in progress (waiting for TUW)
    # Filter trajectories with collision set to True
    collision_trajectories = [t for t in trajectories if t.get('collision', False)]

    if len(collision_trajectories) <= 1:
        logger.error(
            f'[mutate fn] (case2) Not enough collisions to determine lower priority UAV: {collision_trajectories}')
        return False, f'(case2) Not enough collisions to determine lower priority UAV: {collision_trajectories}'

    # Find the trajectory with the highest uav_id (Lower priority)
    lowest_uav_id_trajectory = max(collision_trajectories,
                                   key=lambda t: t['uav_id'])  #TODO proper priority check + PDOP?

    uav_type = lowest_uav_id_trajectory.get('uav_type', None)
    if uav_type is None:
        logger.error(f'[mutate fn] No uav_type key found in trajectory: {lowest_uav_id_trajectory}')
        return False, f' No uav_type key found in trajectory: {lowest_uav_id_trajectory}'

    uav_ability = abilities.get(uav_type, {})
    max_bearing = float(uav_ability.get('max_bearing', 0))

    # NEW: sensible defaults so we don’t end up with 0° change
    if max_bearing <= 0:
        max_bearing = 15.0  # degrees

    min_bearing = 5.0  # don’t do tiny/no-op changes
    sign = -1 if random.random() < 0.5 else 1
    bearing_change = sign * max(min_bearing, random.uniform(0, max_bearing))

    original_dir = lowest_uav_id_trajectory['direction']
    lowest_uav_id_trajectory['direction'] = (original_dir + bearing_change) % 360

    # set flags
    lowest_uav_id_trajectory['origin'] = 'mutate'  # flag the updated trajectory
    lowest_uav_id_trajectory['mutation_cases'] = f"{int(lowest_uav_id_trajectory.get('mutation_cases', '000'), 2) | 0b010:03b}"  # binary flag for Case 2

    # Remove the "collision" key from each trajectory in collision_trajectories
    for trajectory in collision_trajectories:
        if 'collision' in trajectory:
            del trajectory['collision']

    logger.info(
        f"[mutate fn] changed dir of UAV {lowest_uav_id_trajectory['uav_id']} from {original_dir} to {lowest_uav_id_trajectory['direction']}")

    return True, trajectories
