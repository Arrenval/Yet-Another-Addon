from ...props         import Armature, KaosArmature
from .com.sort        import sort_bone_list
from ...xivpy.sklb    import XIVSkeleton, AnimLayer
from .exp.constructor import SklbConstructor


class SklbExport:
    def __init__(self):
        self.sklb = XIVSkeleton()
        self.kaos = self.sklb.kaos

    @classmethod
    def export_armature(cls, armature: Armature, file_path: str, dummy_bones=False) -> None:
        exporter = cls()
        return exporter._create_sklb(armature, file_path, dummy_bones)

    def _create_sklb(self, armature: Armature, file_path: str, dummy_bones: bool) -> None:
        if dummy_bones:
            bone_list = {bone.name for bone in armature.kaos.bone_list}
            self.bone_indices = sort_bone_list(bone_list, dummy_bones)
        else:
            self.bone_indices = armature.kaos.get_bone_indices()
        
        self._set_header(armature.kaos)
        SklbConstructor.from_armature(self.kaos, armature, self.bone_indices)

        self.sklb.header.connect_bone_idx = -1
        self.sklb.to_file(file_path)

    def _set_header(self, arma_kaos: KaosArmature) -> None:
        self.sklb.header.race_id = int(arma_kaos.race_id)
        for id in arma_kaos.get_mappers():
            self.sklb.header.mapper_id.append(id)
        
        for layer in arma_kaos.anim_layers:
            new_layer              = AnimLayer()
            new_layer.id           = layer.id
            new_layer.bone_indices = [self.bone_indices[bone.name] for bone in layer.bone_list]

            self.sklb.anim_data.layers.append(new_layer)
       