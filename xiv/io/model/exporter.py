from bpy.types        import Object
from collections      import defaultdict

from ..logging        import YetAnotherLogger
from .exp.scene       import prepare_submeshes
from .com.exceptions  import XIVMeshError
from .exp.constructor import CreateLOD

from ...formats.model import (XIVModel, NeckMorph,
                              ModelFlags1, ModelFlags2, ModelFlags3)


def get_lod_range(lod_level: int) -> float:
    ranges = {
        0: 38.0,
        1: 126.0,
        2: 0
    }

    return ranges[lod_level]

class ModelExport:
    
    def __init__(self, logger: YetAnotherLogger=None, **model_flags):
        self.model             = XIVModel()
        self.logger            = logger
        self.shape_value_count = 0

        self.model_flags : dict[str, bool]      = model_flags
        self.export_stats: dict[str, list[str]] = defaultdict(list)

    @classmethod
    def export_scene(
                cls, 
                export_obj : list[Object], 
                file_path  : str,
                export_lods: bool,
                neck_morphs: list[tuple[list[float], list[float]]], 
                logger     : YetAnotherLogger=None, 
                **model_flags
            ) -> dict[str, list[str]]:
        
        exporter = cls(logger=logger, **model_flags)
        return exporter._create_model(export_obj, file_path, export_lods, neck_morphs)

    def _create_model(
                self, 
                export_obj : list[Object], 
                file_path  : str, 
                export_lods: bool, 
                neck_morphs: list[tuple[list[float], list[float]]]
                ) -> dict[str, list[str]]:

        origin    = 0.0
        max_lod   = 3 if export_lods else 1
        face_data = any(obj.data.shape_keys.key_blocks.get("shp_sdw_a", False) 
                        for obj in export_obj if obj.data.shape_keys)
        
        for lod_level, active_lod in enumerate(self.model.lods[:max_lod]):
            if self.logger:
                self.logger.last_item = f"LOD{lod_level}"
                self.logger.log(f"Configuring LOD{lod_level}...", 2)
                
            sorted_meshes = prepare_submeshes(export_obj, self.model.attributes, lod_level)
            if not sorted_meshes:
                break

            active_lod.mesh_idx = len(self.model.meshes)

            lod = CreateLOD.construct(
                                self.model, 
                                lod_level,
                                active_lod, 
                                face_data, 
                                sorted_meshes,
                                self.shape_value_count,
                                logger=self.logger
                            )
            
            self.shape_value_count = lod.shape_value_count
            self.export_stats.update(**lod.export_stats)
            self.model.set_lod_count(lod_level + 1)

        lod_count = self.model.header.lod_count
        for lod_level, active_lod in enumerate(self.model.lods[:lod_count]):
            lod_range = 0 if lod_level == (lod_count - 1) else get_lod_range(lod_level)
            active_lod.model_lod_range   = lod_range
            active_lod.texture_lod_range = lod_range

        self.model.bounding_box        = self.model.mdl_bounding_box.copy()
        self.model.bounding_box.min[1] = origin
        self.model.mesh_header.radius  = self.model.bounding_box.radius()

        if neck_morphs:
            self._add_neck_morph(neck_morphs)

        if face_data:
            self.model.face_data["sign"][0] = 1
        
        self._set_flags()
        self.model.to_file(file_path)

        return self.export_stats

    def _set_flags(self) -> None:
        for flag in ModelFlags1:
            if self.model_flags.get(flag.name.lower(), False):
                self.model.mesh_header.flags1 |= flag

        for flag in ModelFlags2:
            if self.model_flags.get(flag.name.lower(), False):
                self.model.mesh_header.flags2 |= flag

        for flag in ModelFlags3:
            if self.model_flags.get(flag.name.lower(), False):
                self.model.mesh_header.flags3 |= flag

    def _add_neck_morph(self, neck_morphs: list[tuple[list[float], list[float]]]) -> None:
        try:
            kubi = self.model.bones.index("j_kubi")
            sebo = self.model.bones.index("j_sebo_c")
        except:
            raise XIVMeshError("Couldn't create neck morph data. Missing 'j_kubi' or 'j_sebo_c'.")
        
        for pos, normals in neck_morphs:
            morph = NeckMorph()
            morph.normals   = normals
            morph.positions = pos
            morph.bone_idx  = [kubi, sebo, 0, 0]
            self.model.neck_morphs.append(morph)
            