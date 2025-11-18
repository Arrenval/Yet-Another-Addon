from mathutils import Vector, Quaternion


def hkvec_to_blend(pos: Vector) -> Vector:
    return Vector((pos.x, -pos.z, pos.y))

def hkquat_to_blend(quat: Quaternion) -> Quaternion:
    return Quaternion((quat.w, quat.x, -quat.z, quat.y))

def blend_to_hkvec(pos: Vector) -> Vector:
    return Vector((pos.y, pos.z, pos.x))

def blend_to_hkquat(quat: Quaternion) -> Quaternion:
    return Quaternion((quat.w, quat.y, quat.z, quat.x))
