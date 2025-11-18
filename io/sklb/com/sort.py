from ..data import get_bone_list


def sort_bone_list(bone_list: list[str], dummy_bones=False) -> dict[str, int]:
    vanilla = get_bone_list('VANILLA')
    ivcs    = get_bone_list('IVCS')
    v_count = len(vanilla)

    ivcs_idx = 250
    sort_key = {}
    for idx, bone in enumerate(vanilla + ivcs):
        sort_key[bone] = idx
    
    if dummy_bones:
        dummy_idx   = v_count
        dummy_count = ivcs_idx - v_count
        for i in range(dummy_count):
            dummy_name = f"xiv_dmy_{i}"
            sort_bone_list[dummy_name] = dummy_idx
            bone_list.append(dummy_name)
            dummy_idx += 1

    bone_list = sorted(bone_list, key=lambda x: sort_key.get(x, 9999))
    return {bone: idx for idx, bone in enumerate(bone_list)}
