import enum
import random
import string
from abc import abstractmethod
from typing import Optional

from acto.schema import (
    AnyOfSchema,
    ArraySchema,
    BooleanSchema,
    IntegerSchema,
    NumberSchema,
    ObjectSchema,
    OpaqueSchema,
    StringSchema,
)
from acto.utils import get_thread_logger


class ValueWithSchema:
    """A concrete value with a schema attached"""

    def __init__(self) -> None:
        pass

    @abstractmethod
    def raw_value(self) -> object:
        """Return the raw value of the object"""
        return None

    @abstractmethod
    def mutate(self, p_delete=0.05, p_replace=0.1):
        """Mutate a small portion of the value"""
        return

    @abstractmethod
    def update(self, value):
        """Update the value with a new value"""
        return

    @abstractmethod
    def get_value_by_path(self, path: list):
        """Fetch the value specified by path"""
        return

    @abstractmethod
    def create_path(self, path: list):
        """Ensures the path exists"""
        return

    @abstractmethod
    def set_value_by_path(self, value, path):
        """Set the value specified by path"""
        return

    @abstractmethod
    def value(self):
        """Return the value"""
        return


class ValueWithObjectSchema(ValueWithSchema):
    """Value with ObjectSchema attached"""

    def __init__(self, value, schema) -> None:
        self.schema = schema
        if value is None:
            self.store = None
        elif isinstance(value, dict):
            self.store = {}
            for k, v in value.items():
                self.store[k] = attach_schema_to_value(
                    v, self.schema.get_property_schema(k)
                )
        else:
            raise TypeError(
                f"Value [{value}] has type [{type(value)}] Path [{self.schema.get_path()}]"
            )

    def value(self):
        """Return the value"""
        return self.store

    def __str__(self) -> str:
        if self.store is None:
            ret = None
        else:
            ret = {}
            for k, v in self.store.items():
                ret[k] = str(v.raw_value())
        return str(ret)

    def raw_value(self) -> dict:
        if self.store is None:
            return None
        else:
            ret = {}
            for k, v in self.store.items():
                ret[k] = v.raw_value()
            return ret

    def mutate(self, p_delete=0.05, p_replace=0.1):
        """Mutate a small portion of the value

        - Replace with null
        - Replace with a new value
        - mutate a child
        TODO: generate a property that didn't exist before
        """
        logger = get_thread_logger(with_prefix=True)

        if self.store is None:
            value = self.schema.gen()
            self.update(value)
        else:
            dice = random.random()
            if dice < p_delete:
                self.store = None
            elif dice < p_replace:
                value = self.schema.gen()
                self.update(value)
            else:
                properties = self.schema.get_properties()
                if len(properties) == 0:
                    # XXX: Handle additional properties better
                    if self.schema.get_additional_properties() is None:
                        logger.warning(
                            "Object schema is opaque %s", self.schema.get_path()
                        )
                        return
                    else:
                        letters = string.ascii_lowercase
                        key = "".join(random.choice(letters) for i in range(5))
                        self[
                            key
                        ] = self.schema.get_additional_properties().gen()
                else:
                    child_key = random.choice(
                        list(self.schema.get_properties())
                    )
                    if child_key not in self.store:
                        self[child_key] = (
                            self.schema.get_property_schema(child_key).gen(),
                        )
                    self.store[child_key].mutate()

    def update(self, value):
        if value is None:
            self.store = None
        if isinstance(value, enum.Enum):
            value = value.value
        if isinstance(value, dict):
            self.store = {}
            for k, v in value.items():
                self.store[k] = attach_schema_to_value(
                    v, self.schema.get_property_schema(k)
                )
        else:
            raise TypeError(f"Value [{value}] Path [{self.schema.get_path()}]")

    def get_value_by_path(self, path: list):
        """Fetch the value specified by path"""
        if self.store is None:
            return None
        if len(path) == 0:
            return self.raw_value()
        key = path.pop(0)
        if key not in self.store:
            # path does not exist yet
            return None
        else:
            return self.store[key].get_value_by_path(path)

    def create_path(self, path: list):
        """Ensures the path exists"""
        if len(path) == 0:
            return
        key = path.pop(0)
        if self.store is None:
            self.update(self.schema.gen(minimum=True))
            self[key] = None
        elif key not in self.store:
            self[key] = None
        self.store[key].create_path(path)

    def set_value_by_path(self, value, path):
        if len(path) == 0:
            self.update(value)
        else:
            key = path.pop(0)
            self.store[key].set_value_by_path(value, path)

    def __getitem__(self, key):
        return self.store[key]

    def __setitem__(self, key, value):
        self.store[key] = attach_schema_to_value(
            value, self.schema.get_property_schema(key)
        )

    def __contains__(self, item: str):
        # in operator
        return item in self.store


class ValueWithArraySchema(ValueWithSchema):
    """Value with ArraySchema attached"""

    def __init__(self, value, schema) -> None:
        self.schema = schema
        if value is None:
            self.store = None
        elif isinstance(value, list):
            self.store = []
            for i in value:
                self.store.append(
                    attach_schema_to_value(i, self.schema.get_item_schema())
                )
        else:
            raise TypeError(f"Value [{value}] Path [{self.schema.get_path()}]")

    def value(self):
        return self.store

    def __str__(self) -> str:
        if self.store is None:
            return "None"
        else:
            ret = []
            for i in self.store:
                ret.append(str(i.raw_value()))
            return str(ret)

    def raw_value(self) -> list:
        if self.store is None:
            return None
        else:
            ret = []
            for i in self.store:
                ret.append(i.raw_value())
            return ret

    def mutate(self, p_delete=0.05, p_replace=0.1):
        """Mutate a small portion of the value

        - Replace with null
        - Delete an item
        - Append an item
        - mutate an item
        """
        if self.store is None:
            value = self.schema.gen()
            self.update(value)
        elif len(self.store) == 0:
            self.append(self.schema.get_item_schema().gen())
        else:
            dice = random.random()
            if dice < p_delete:
                self.store = None
            elif dice < 0.4:
                # Delete an item
                index = random.randint(0, len(self.store) - 1)
                del self.store[index]
            elif dice < 0.7:
                # Append an item
                self.append(self.schema.get_item_schema().gen())
            else:
                # mutate an item
                index = random.randint(0, len(self.store) - 1)
                self.store[index].mutate()

    def update(self, value):
        if value is None:
            self.store = None
        if isinstance(value, enum.Enum):
            value = value.value
        elif isinstance(value, list):
            self.store = []
            for i in value:
                self.store.append(
                    attach_schema_to_value(i, self.schema.get_item_schema())
                )
        else:
            raise TypeError(f"Value [{value}] Path [{self.schema.get_path()}]")

    def append(self, value):
        """Append a value to the array"""
        self.store.append(
            attach_schema_to_value(value, self.schema.get_item_schema())
        )

    def get_value_by_path(self, path: list):
        """Fetch the value specified by path"""
        if self.store is None:
            return None
        if len(path) == 0:
            return self.raw_value()
        key = path.pop(0)
        if key >= len(self.store):
            # path does not exist yet
            return None
        else:
            return self.store[key].get_value_by_path(path)

    def create_path(self, path: list):
        """Ensures the path exists"""
        if len(path) == 0:
            return
        key = path.pop(0)
        if self.store is None:
            self.store = []
            for _ in range(0, key):
                self.append(None)
            self.append(None)
        elif key >= len(self.store):
            for _ in range(len(self.store), key):
                self.append(None)
            self.append(None)
        self.store[key].create_path(path)

    def set_value_by_path(self, value, path):
        if len(path) == 0:
            self.update(value)
        else:
            key = path.pop(0)
            self.store[key].set_value_by_path(value, path)

    def __getitem__(self, key):
        return self.store[key]

    def __setitem__(self, key, value):
        self.store[key] = attach_schema_to_value(
            value, self.schema.get_item_schema()
        )

    def __contains__(self, item: int):
        # in operator
        return item < len(self.store)


class ValueWithAnyOfSchema(ValueWithSchema):
    """Value with AnyOfSchema attached

    store here is an instance of ValueWithSchema
    """

    def __init__(self, value, schema) -> None:
        self.schema = schema
        if value is None:
            self.store = None

        for possible_schema in self.schema.get_possibilities():
            if self.__validate(value, possible_schema):
                self.store = attach_schema_to_value(value, possible_schema)
                return
        raise TypeError(f"Value [{value}] Path [{self.schema.get_path()}]")

    def __validate(self, value, schema) -> bool:
        # XXX: Fragile! Use a complete validation utility from library
        if value is None:
            return True
        elif isinstance(value, dict) and isinstance(schema, ObjectSchema):
            return True
        elif isinstance(value, list) and isinstance(schema, ArraySchema):
            return True
        elif isinstance(value, str) and isinstance(schema, StringSchema):
            return True
        elif isinstance(value, bool) and isinstance(schema, BooleanSchema):
            return True
        elif isinstance(value, int) and isinstance(schema, IntegerSchema):
            return True
        elif isinstance(value, (float, int)) and isinstance(
            schema, NumberSchema
        ):
            return True
        else:
            return False

    def __str__(self) -> str:
        if self.schema is None:
            ret = "None"
        else:
            ret = str(self.store)
        return ret

    def raw_value(self) -> Optional[dict]:
        """serialization"""
        if self.store is None:
            return None
        else:
            return self.store.raw_value()

    def mutate(self, p_delete=0.05, p_replace=0.1):
        """Mutate a small portion of the value

        - Replace with null
        - Replace with a new value
        - Mutate depend on the current schema
        """
        if self.store is None:
            value = self.schema.gen()
            self.update(value)
        else:
            dice = random.random()
            if dice < p_delete:
                self.store = None
            elif dice < p_replace:
                self.update(self.schema.gen())
            else:
                self.store.mutate()

    def update(self, value):
        if value is None:
            self.store = None
        else:
            for possible_schema in self.schema.get_possibilities():
                if self.__validate(value, possible_schema):
                    self.store = attach_schema_to_value(value, possible_schema)
                    return
            raise TypeError(f"Value [{value}] Path [{self.schema.get_path()}]")

    def get_value_by_path(self, path: list):
        """Fetch the value specified by path"""
        if self.store is None:
            return None
        else:
            return self.store.get_value_by_path(path)

    def create_path(self, path: list):
        """Ensures the path exists"""

        # XXX: Complicated, no use case yet, let's implement later
        raise NotImplementedError

    def set_value_by_path(self, value, path):
        if len(path) == 0:
            self.update(value)
        else:
            self.store.set_value_by_path(value, path)


class ValueWithBasicSchema(ValueWithSchema):
    """Value with schema attached for Number/Integer, Bool, String"""

    def __init__(self, value, schema) -> None:
        self.schema = schema
        if value is None:
            self.store = None
        else:
            self.store = value

    def value(self):
        return self.store

    def __str__(self) -> str:
        if self.store is None:
            ret = "None"
        else:
            ret = str(self.store)
        return ret

    def raw_value(self) -> Optional[dict]:
        """serialization"""
        return self.store

    def mutate(self, p_delete=0.05, p_replace=0.1):
        """Generate a new value or set to null"""
        if self.store is None:
            self.store = self.schema.gen()
        else:
            dice = random.random()
            if dice < p_delete:
                self.store = None
            else:
                self.update(self.schema.gen())

    def update(self, value):
        if value is None:
            self.store = None
        else:
            if isinstance(value, enum.Enum):
                value = value.value
            self.store = value

    def get_value_by_path(self, path: list):
        if len(path) > 0:
            raise RuntimeError("Reached basic value, but path is not exhausted")
        return self.store

    def create_path(self, path: list):
        if len(path) == 0:
            return
        else:
            raise RuntimeError("Reached basic value, but path is not exhausted")

    def set_value_by_path(self, value, path):
        if len(path) == 0:
            self.update(value)
        else:
            raise RuntimeError("Reached basic value, but path is not exhausted")


class ValueWithOpaqueSchema(ValueWithSchema):
    """Value with an opaque schema"""

    def __init__(self, value, schema) -> None:
        self.schema = schema
        self.store = value

    def raw_value(self) -> object:
        return self.store

    def mutate(self, p_delete=0.05, p_replace=0.1):
        return

    def update(self, value):
        if isinstance(value, enum.Enum):
            value = value.value
        self.store = value

    def get_value_by_path(self, path: list):
        return self.store

    def create_path(self, path: list):
        return

    def set_value_by_path(self, value, path):
        self.store = value

    def value(self):
        return self.store


def attach_schema_to_value(value, schema):
    """Attach schema to value and return a ValueWithSchema object"""
    if isinstance(schema, ObjectSchema):
        return ValueWithObjectSchema(value, schema)
    elif isinstance(schema, ArraySchema):
        return ValueWithArraySchema(value, schema)
    elif isinstance(schema, AnyOfSchema):
        return ValueWithAnyOfSchema(value, schema)
    elif isinstance(schema, OpaqueSchema):
        return ValueWithOpaqueSchema(value, schema)
    else:
        return ValueWithBasicSchema(value, schema)
