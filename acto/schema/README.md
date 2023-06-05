# Module for parsing the [OpenAPISchema](https://swagger.io/specification/)

This module supports 6 basic primitive types in JSON/YAML:
- [Array](array.py)
- [Boolean](boolean.py)
- [Integer](integer.py)/[Number](number.py)
- [Object](object.py)
- [String](string.py)

All classes implement the interface defined in `base.py`

This module also supports representing the schemas in a tree structure to aid input generation.