# (c) Copyright 2009 Cloudera, Inc.
#
# AllTests for stitch.util
# TODO: Add your test suites to the list here

import sys
import unittest
from stitch.util.propertiestest import PropertiesTest

def testSuite():
  # TODO: Add your test suites to the list here.
  propsSuite = unittest.makeSuite(PropertiesTest, 'test')

  alltests = unittest.TestSuite([propsSuite])
  return alltests

if __name__ == "__main__":
  runner = unittest.TextTestRunner()
  sys.exit(not runner.run(testSuite()).wasSuccessful())

