#!/usr/bin/env python3
"""Test runner for lxrpy."""

import os
import sys
import unittest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_tests():
    """Discover and run all tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Discover tests in tests/ directory
    discovered_tests = loader.discover('tests', pattern='test_*.py')
    suite.addTest(discovered_tests)

    # Run with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_tests())
