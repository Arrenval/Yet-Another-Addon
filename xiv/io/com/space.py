from numpy.typing import NDArray

def xiv_to_blend_space(array: NDArray) -> NDArray:
        y_axis = array[:, 1].copy()
        z_axis = array[:, 2].copy()

        array[:, 1] = -z_axis
        array[:, 2] = y_axis

        return array

def blend_to_xiv_space(array: NDArray) -> NDArray:
    y_axis = array[:, 1].copy()
    z_axis = array[:, 2].copy()

    array[:, 1] = z_axis
    array[:, 2] = -y_axis

    return array 
        