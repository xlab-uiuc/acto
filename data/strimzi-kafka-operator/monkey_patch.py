from acto.monkey_patch.monkey_patch import patch_mro

patch_mro('QuantitySchema', ['K8sStringSchema'])
