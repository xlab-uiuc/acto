import unittest

from acto.post_process.post_diff_test import compute_common_regex


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


if __name__ == "__main__":
    unittest.main()
