""""""

from typing import Literal, Optional

import pydantic

from acto.common import PropertyPath


class XorCondition(pydantic.BaseModel):
    """Condition that is the xor of two properties"""

    left: PropertyPath
    right: PropertyPath
    type: Literal["xor"]

    def solve(
        self, assumptions: list[tuple[PropertyPath, bool]]
    ) -> Optional[tuple[PropertyPath, bool]]:
        """Solve the condition given the assumptions"""
        left = None
        right = None
        for assumption in assumptions:
            if assumption[0] == self.left:
                left = assumption[1]
            if assumption[0] == self.right:
                right = assumption[1]
        if left is None and right is None:
            return None
        if left is None and right is not None:
            return (self.left, not right)
        if left is not None and right is None:
            return (self.right, not left)
        return None


# class Condition:

#     def __init__(self) -> None:
#         pass


# class Value(abc.ABC):

#     def __init__(self) -> None:
#         pass

#     def resolve(self, cr: ValueWithSchema) -> Any:
#         pass


# class PropertyValue(Value):

#     def __init__(self, property_path: PropertyPath) -> None:
#         self.property_path = property_path

#     def resolve(self, cr: ValueWithSchema) -> Any:
#         return cr.get_value_by_path(self.property_path.path)


# class ConstantValue(Value):

#     def __init__(self, value: Any) -> None:
#         self.value = value

#     def resolve(self, cr: ValueWithSchema) -> Any:
#         return self.value


# class EqualCondition(Condition):

#     def __init__(self, left: Value, right: Value) -> None:
#         self.left = left
#         self.right = right

#     def solve(
#         self, cr: ValueWithSchema, assumptions: list[Condition]
#     ) -> Optional[list[Condition]]:
#         return self.left.resolve(cr) == self.right.resolve(cr)


# class XorCondition(Condition):

#     def __init__(self, left: Condition, right: Condition) -> None:
#         self.left = left
#         self.right = right

#     def solve(self, cr: ValueWithSchema) -> bool:
#         return self.left.solve(cr) ^ self.right.solve(cr)
