from unittest import TestCase

from acto.lib.dict import visit_dict

test_dict = {
    "a": {
        "b": "",
        "c": {
            "d": None
        }
    }
}


class Test(TestCase):
    def test_visit_dict(self):
        self.assertEqual((True, test_dict), visit_dict(test_dict, []))
        self.assertEqual((True, test_dict["a"]), visit_dict(test_dict, ["a"]))
        self.assertEqual((True, test_dict["a"]["b"]), visit_dict(test_dict, ["a", "b"]))
        self.assertEqual((True, test_dict["a"]["c"]), visit_dict(test_dict, ["a", "c"]))
        self.assertEqual((True, test_dict["a"]["c"]["d"]), visit_dict(test_dict, ["a", "c", "d"]))
        self.assertEqual((False, None), visit_dict(test_dict, ["a", "c", "e"]))
        self.assertEqual((False, None), visit_dict(test_dict, ["a", "e"]))
        self.assertEqual((False, None), visit_dict(test_dict, ["e"]))
        self.assertEqual((False, None), visit_dict(test_dict, ["a", "b", "c"]))
        self.assertEqual((False, None), visit_dict(test_dict, ["b", "b", "c"]))
