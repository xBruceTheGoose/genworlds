"""Unit tests for the YAML class loader allowlist."""
import pytest
from unittest.mock import patch
import importlib

import sys


class TestLoadClass:
    def test_allowed_genworlds_prefix(self):
        from use_cases.roundtable.world_setup import load_class
        # Should not raise
        cls = load_class("genworlds.simulation.simulation.Simulation")
        from genworlds.simulation.simulation import Simulation
        assert cls is Simulation

    def test_allowed_use_cases_prefix(self):
        from use_cases.roundtable.world_setup import load_class
        cls = load_class("use_cases.roundtable.world_setup.load_yaml")
        assert callable(cls)

    def test_blocked_os_module(self):
        from use_cases.roundtable.world_setup import load_class
        with pytest.raises(ValueError, match="untrusted module"):
            load_class("os.path.join")

    def test_blocked_builtins(self):
        from use_cases.roundtable.world_setup import load_class
        with pytest.raises(ValueError, match="untrusted module"):
            load_class("builtins.eval")

    def test_blocked_arbitrary_package(self):
        from use_cases.roundtable.world_setup import load_class
        with pytest.raises(ValueError, match="untrusted module"):
            load_class("subprocess.Popen")
