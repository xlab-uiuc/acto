import unittest

from deepdiff import DeepDiff
from deepdiff.helper import CannotCompare

from acto.post_process.post_diff_test import (
    NameOperator,
    compare_func,
    compute_common_regex,
)


class TestPostDiffTest(unittest.TestCase):
    """Test PostDiffTest"""

    def test_compute_common_regex_prefix(self):
        """Test computing common regex"""
        testdata = [
            "root['pod_disruption_budget']['test-cluster-pdb']",
            "root['pod_disruption_budget']['test-cluster-pda']",
            "root['pod_disruption_budget']['test-cluster-pdc']",
            "root['pod_disruption_budget']['test-cluster-pdd']",
        ]
        self.assertCountEqual(
            compute_common_regex(testdata),
            ["^root\\['pod_disruption_budget'\\]\\['test\\-cluster\\-pd.*$"],
        )

    def test_compute_common_regex_suffix(self):
        """Test computing common regex"""
        testdata = [
            "root['pod_disruption_budget']['test-cluster-pda']['metadata']['name']",
            "root['pod_disruption_budget']['test-cluster-pdb']['metadata']['name']",
            "root['pod_disruption_budget']['test-cluster-pdc']['metadata']['name']",
            "root['pod_disruption_budget']['test-cluster-pdd']['metadata']['name']",
            "root['pod_disruption_budget']['test-cluster-pde']['metadata']['name']",
        ]
        self.assertCountEqual(
            compute_common_regex(testdata),
            [
                "^root\\['pod_disruption_budget'\\]"
                "\\['test\\-cluster\\-pd.*'\\]\\['metadata'\\]\\['name'\\]$"
            ],
        )

    def test_compute_common_regex_different_resources(self):
        """Test computing common regex"""
        testdata = [
            "root['secret']['my-secret']",
            "root['pod_disruption_budget']['test-cluster-pdb']['metadata']['name']",
            "root['pod_disruption_budget']['test-cluster-pdc']['metadata']['name']",
            "root['pod_disruption_budget']['test-cluster-pdd']['metadata']['name']",
            "root['pod_disruption_budget']['test-cluster-pde']['metadata']['name']",
            "root['pod_disruption_budget']['test-cluster-pde']['metadata']['namespace']",
        ]
        self.assertCountEqual(
            compute_common_regex(testdata),
            [
                "^root\\['pod_disruption_budget'\\]"
                "\\['test\\-cluster\\-pde'\\]\\['metadata'\\]\\['namespace'\\]$",
                "^root\\['secret'\\]\\['my\\-secret'\\]$",
                "^root\\['pod_disruption_budget'\\]"
                "\\['test\\-cluster\\-pd.*'\\]\\['metadata'\\]\\['name'\\]$",
            ],
        )

    def test_compute_common_regex_secret(self):
        """Test computing common regex"""
        testdata = [
            "root['secret']['my-secret-vczvds']",
            "root['secret']['my-secret-adsfas']",
            "root['secret']['my-secret-sfdsdf']",
        ]
        self.assertCountEqual(
            compute_common_regex(testdata),
            ["^root\\['secret'\\]\\['my\\-secret\\-.*.*.*$"],
        )

    def test_compute_common_regex_complex(self):
        """Test computing common regex"""
        testdata = [
            "root['secret']['my-secret-vczvds']",
            "root['secret']['my-secret-adsfas']",
            "root['secret']['my-secret-bbbdfs']",
            "root['pod_disruption_budget']['test-cluster-pdb']['metadata']['name']",
            "root['pod_disruption_budget']['test-cluster-pdc']['metadata']['name']",
            "root['pod_disruption_budget']['test-cluster-pdd']['metadata']['name']",
            "root['pod_disruption_budget']['test-cluster-pde']['metadata']['name']",
            "root['pod_disruption_budget']['test-cluster-pde']['metadata']['namespace']",
            "root['pod_disruption_budget']['test-cluster-pde']['metadata']['namespace']",
            "root['pod_disruption_budget']['test-cluster-pde']['metadata']['namespace']",
            "root['pod_disruption_budget']['test-cluster-pde']['metadata']['namespace']",
            "root['pod_disruption_budget']['test-cluster-pde']['metadata']['namespace']",
            "root['pod_disruption_budget']['test-cluster-pde']['metadata']['namespace']",
            "root['pod_disruption_budget']['test-cluster-pde']['metadata']['namespace']",
            "root['pod_disruption_budget']['test-cluster-pde']['metadata']['namespace']",
            "root['pod_disruption_budget']['test-cluster-pde']['metadata']['namespace']",
        ]
        self.assertCountEqual(
            compute_common_regex(testdata),
            [
                "^root\\['secret'\\]\\['my\\-secret\\-.*.*.*$",
                "^root\\['pod_disruption_budget'\\]"
                "\\['test\\-cluster\\-pd.*'\\]\\['metadata'\\]\\['name'\\]$",
                "^root\\['pod_disruption_budget'\\]"
                "\\['test\\-cluster\\-pde'\\]\\['metadata'\\]\\['namespace'\\]$",
            ],
        )


class TestCompareFunc(unittest.TestCase):
    """Test the list item pairing used by the differential oracle"""

    @staticmethod
    def diff(prev, curr):
        """Diff the way compare_system_equality does"""
        return DeepDiff(
            prev,
            curr,
            iterable_compare_func=compare_func,
            ignore_order=True,
            custom_operators=[NameOperator(r".*\['name'\]$")],
            view="tree",
        )

    def test_key_operator(self):
        """Items with the same key and operator are the same item"""
        toleration = {"key": "a", "operator": "Exists", "effect": "NoSchedule"}
        self.assertTrue(
            compare_func(toleration, {**toleration, "effect": "NoExecute"})
        )
        self.assertFalse(compare_func(toleration, {**toleration, "key": "b"}))
        self.assertFalse(
            compare_func(toleration, {**toleration, "operator": "Equal"})
        )

    def test_type(self):
        """Pod conditions are paired by type"""
        self.assertTrue(
            compare_func(
                {"type": "Ready", "status": "True"},
                {"type": "Ready", "status": "False"},
            )
        )
        self.assertFalse(
            compare_func({"type": "Ready"}, {"type": "Initialized"})
        )

    def test_cannot_compare(self):
        """Items without a name, key or type fall back to the default pairing"""
        with self.assertRaises(CannotCompare):
            compare_func({"image": "a"}, {"image": "b"})
        with self.assertRaises(CannotCompare):
            compare_func("a", "b")

    def test_generated_name_suffix_ignored(self):
        """Names that differ only in the generated suffix are the same item"""
        self.assertTrue(
            compare_func({"name": "data-abcde"}, {"name": "data-x7k2p"})
        )
        self.assertTrue(
            compare_func({"name": "ab-abcde"}, {"name": "ab-x7k2p"})
        )

    def test_names_sharing_a_prefix_differ(self):
        """A shared five character prefix does not make two names the same"""
        self.assertFalse(
            compare_func(
                {"name": "test-cluster-config-abcde"},
                {"name": "test-cluster-secret-x7k2p"},
            )
        )
        self.assertFalse(
            compare_func({"name": "cluster-0"}, {"name": "cluster-1"})
        )

    def test_replaced_volume_is_reported(self):
        """Replacing a generated-name volume by a different one is a diff"""
        diff = self.diff(
            {"volumes": [{"name": "test-cluster-config-abcde", "size": 1}]},
            {"volumes": [{"name": "test-cluster-secret-x7k2p", "size": 1}]},
        )
        self.assertTrue(diff)

    def test_regenerated_name_is_not_reported(self):
        """A volume whose generated suffix changed is not a diff"""
        diff = self.diff(
            {"volumes": [{"name": "test-cluster-config-abcde", "size": 1}]},
            {"volumes": [{"name": "test-cluster-config-x7k2p", "size": 1}]},
        )
        self.assertFalse(diff)
        diff = self.diff(
            {"volumes": [{"name": "web-abcde", "size": 1}]},
            {"volumes": [{"name": "web-x7k2p", "size": 1}]},
        )
        self.assertFalse(diff)

    def test_conditions_paired_by_type(self):
        """A condition is compared with the condition of the same type"""
        types = ["Initialized", "Ready", "ContainersReady", "PodScheduled"]

        def conditions(*statuses):
            return {
                "conditions": [
                    {"type": t, "status": s} for t, s in zip(types, statuses)
                ]
            }

        diff = self.diff(
            conditions("True", "True", "True", "False"),
            conditions("True", "True", "False", "True"),
        )
        self.assertEqual(list(diff.keys()), ["values_changed"])
        self.assertEqual(
            sorted(level.path() for level in diff["values_changed"]),
            [
                "root['conditions'][2]['status']",
                "root['conditions'][3]['status']",
            ],
        )


if __name__ == "__main__":
    unittest.main()
