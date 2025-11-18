import numpy as np

from numpy        import single
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

def tangent_to_world_space(world_vectors: NDArray, tangents: NDArray, bitangents: NDArray, normals: NDArray) -> NDArray:
    # This is equivalent to transposing a regular TBN matrix.
    tbn_matrices = np.zeros((len(tangents), 3, 3), dtype=single)
    tbn_matrices[:, 0, :] = tangents      
    tbn_matrices[:, 1, :] = bitangents    
    tbn_matrices[:, 2, :] = normals  
    
    return (tbn_matrices @ world_vectors[..., np.newaxis]).squeeze(-1)

def world_to_tangent_space(tangent_vectors: NDArray, tangents: NDArray, bitangents: NDArray, normals: NDArray) -> NDArray:
    tbn_matrices = np.zeros((len(tangents), 3, 3), dtype=single)
    tbn_matrices[:, :, 0] = tangents      
    tbn_matrices[:, :, 1] = bitangents    
    tbn_matrices[:, :, 2] = normals  
    
    return (tbn_matrices @ tangent_vectors[..., np.newaxis]).squeeze(-1)

# from https://github.com/dofuuz/colorspace_convertor/blob/main/color_srgb.py
def lin_to_srgb(lin: NDArray) -> NDArray:
    abs_lin = np.abs(lin)
    abs_gam = np.where(
                    abs_lin <= 0.0031308,
                    12.92 * abs_lin,
                    1.055 * np.power(abs_lin, 1/2.4) - 0.055
                )
    return np.sign(lin) * abs_gam

def srgb_to_lin(gam: NDArray) -> NDArray:
    abs_gam = np.abs(gam)
    abs_lin = np.where(
                    abs_gam <= 0.040449936,
                    abs_gam / 12.92,
                    np.power((abs_gam + 0.055) / 1.055, 2.4)
                )
    return np.sign(gam) * abs_lin
