import unittest

from .get_total_number_schemas import get_total_number_schemas


class TestGetTotalNumberSchemas(unittest.TestCase):
    """Tests for get_total_number_schemas()."""

    def test_simple_get_total_number_schemas(self):
        """Test simple case of getting total number of schemas."""

        schema = {
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"},
                "c": {"type": "number"},
            },
            "type": "object",
        }
        num = get_total_number_schemas(schema)

        assert num == 4
