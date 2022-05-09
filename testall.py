#!/bin/env python

from optparse import OptionParser
import sys
try:
    import unittest2 as unittest
except (ImportError, NameError):
    import unittest


def test():
    parser = OptionParser()
    parser.add_option("-n", "--num", default=1, help="Number of loops")
    parser.add_option("-a", "--run_all", action='store_true', help="Run all tests (including visual)")
    parser.add_option("-p", "--pattern", help="Run a custom Pattern to find")
    parser.add_option("-f", "--folder", default="tests")
    parser.add_option("-v", "--verbose", default=2)

    args = parser.parse_args()[0]

    if args.pattern:
        pattern = args.pattern
    elif args.run_all:
        pattern = "*test*.py"
    else:
        pattern = "test*.py"

    loader = unittest.TestLoader().discover(args.folder, pattern)

    for i in range(int(args.num)):
        print("\n\n>>> Running ("+str(i+1)+"/"+str(args.num)+")")
        test_results = unittest.TextTestRunner(verbosity=int(args.verbose)).run(loader)
        #print(">>> Errors: " + str(test_results.errors))
        #print(">>> Failures: " + str(test_results.failures))

    print("return: "+str(not test_results.wasSuccessful()))
    sys.exit(not test_results.wasSuccessful())

def test_typings() -> int:
    import mypy.api
    stdout, _, return_value = mypy.api.run(["--config-file", "mypy.ini", "openglider"])
    print(stdout)
    return return_value
    
if __name__ == "__main__":
    if test_typings():
        sys.exit(1)
    
    test()
