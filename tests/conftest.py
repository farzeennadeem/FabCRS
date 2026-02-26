# FabCRS Test Configuration

import os
import sys
import pytest

# Add FabSim3 to path if running tests from FabCRS directory
fabsim_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if os.path.exists(os.path.join(fabsim_root, "fabsim")):
    sys.path.insert(0, fabsim_root)
