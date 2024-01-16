"""Integration tests for Acto serialization."""
import os
import pathlib
import unittest

from acto.trial import Trial

test_dir = pathlib.Path(__file__).parent.resolve()
test_data_dir = os.path.join(test_dir, "test_data")


class TestSerialization(unittest.TestCase):
    """Integration tests for Acto serialization."""

    def test_trial_loading(self):
        """Test serialization."""
        cassop_315_trial = os.path.join(
            test_data_dir, "cassop-315", "trial-00-0000"
        )
        trial = Trial.load(cassop_315_trial)
        assert len(trial.steps) == 3
