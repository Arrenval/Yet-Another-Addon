from mathutils import Matrix

def hkmat_to_blend() -> Matrix:
    return Matrix((
        [1.0,  0.0,  0.0, 0.0], 
        [0.0,  0.0,  1.0, 0.0], 
        [0.0, -1.0,  0.0, 0.0], 
        [0.0,  0.0,  0.0, 1.0]  
    ))
