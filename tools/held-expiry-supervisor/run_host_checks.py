#!/usr/bin/env python3
"""Record real pass/skip counts for the supervisor's Linux host tests."""
import argparse
import json
from pathlib import Path
import sys
import unittest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', required=True, type=Path)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    suite = unittest.defaultTestLoader.discover(str(here), pattern='test_*.py')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {'discovered': result.testsRun, 'skipped': len(result.skipped),
              'passed': result.testsRun-len(result.skipped)-len(result.failures)-len(result.errors),
              'failures': len(result.failures), 'errors': len(result.errors),
              'skip_details': [{'test':str(test),'reason':reason} for test,reason in result.skipped],
              'qnx_execution':False}
    args.json.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return 0 if result.wasSuccessful() and report['passed'] >= 34 else 1


if __name__ == '__main__':
    raise SystemExit(main())
