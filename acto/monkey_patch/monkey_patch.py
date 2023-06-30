from typing import Callable, Any
from patch_mro import patch


def init_override(name, old_init):
    def r(self, *args, **kwargs):
        if name in MonkeyPatchSupportMetaClass.override_class_methods and '__init__' in MonkeyPatchSupportMetaClass.override_class_methods[name]:
            MonkeyPatchSupportMetaClass.override_class_methods[name]['__init__'](self, *args, **kwargs)
        else:
            old_init(self, *args, **kwargs)

    return r


class MonkeyPatchSupportMetaClass(type):
    override_class_methods: dict[str, dict[str, Callable]] = {}

    patched_class_instance_attrs: dict[int, dict[str, Any]] = {}
    patched_class_instance_names: dict[int, str] = {}

    def __getattr__(self, attr_name):
        instance_id = id(self)
        if instance_id in MonkeyPatchSupportMetaClass.patched_class_instance_names:
            classname = MonkeyPatchSupportMetaClass.patched_class_instance_names[instance_id]
            if classname in MonkeyPatchSupportMetaClass.override_class_methods and attr_name in MonkeyPatchSupportMetaClass.override_class_methods[classname]:
                return MonkeyPatchSupportMetaClass.override_class_methods[classname][attr_name]

        if instance_id not in MonkeyPatchSupportMetaClass.patched_class_instance_attrs:
            raise AttributeError(f"Attribute {attr_name} not found")
        if attr_name not in MonkeyPatchSupportMetaClass.patched_class_instance_attrs[instance_id]:
            raise AttributeError(f"Attribute {attr_name} not found")
        return MonkeyPatchSupportMetaClass.patched_class_instance_attrs[instance_id][attr_name]

    def __setattr__(self, attr_name, value):
        instance_id = id(self)
        if instance_id not in MonkeyPatchSupportMetaClass.patched_class_instance_attrs:
            MonkeyPatchSupportMetaClass.patched_class_instance_attrs[instance_id] = {}
        if instance_id in MonkeyPatchSupportMetaClass.patched_class_instance_names:
            classname = MonkeyPatchSupportMetaClass.patched_class_instance_names[instance_id]
            if classname in MonkeyPatchSupportMetaClass.override_class_methods and attr_name in MonkeyPatchSupportMetaClass.override_class_methods[classname]:
                raise AttributeError(f"Attribute {attr_name} is read-only")
        else:
            MonkeyPatchSupportMetaClass.patched_class_instance_attrs[instance_id][attr_name] = value

    def __new__(cls, name, bases, attrs):
        old_init = attrs['__init__'] if '__init__' in attrs else None

        def init_func(self, *args, **kwargs):
            if old_init:
                old_init(self, *args, **kwargs)
            else:
                super(cls).__init__(self, *args, **kwargs)

        attrs['__init__'] = init_override(name, init_func)

        proxy_attrs = {}
        for (key, value) in attrs.items():
            if key.startswith('__') and key.endswith('__') and key != '__init__':
                proxy_attrs[key] = value

        patched_class = (super(MonkeyPatchSupportMetaClass, cls).__new__(cls, name, bases, proxy_attrs))

        MonkeyPatchSupportMetaClass.patched_class_instance_attrs[id(patched_class)] = attrs
        MonkeyPatchSupportMetaClass.patched_class_instance_names[id(patched_class)] = name
        return patched_class


def patch_mro(current_class, override_class):
    patch(current_class, override_class)
