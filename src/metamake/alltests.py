# (c) Copyright 2009 Cloudera, Inc.
#
# AllTests for the Metamake project

import sys
import unittest

import metamake.targets.packagetargettest as packagetargettest

def testSuite():
  dir_comp_suite = unittest.makeSuite(packagetargettest.CopyDirTest, 'test')

  alltests = unittest.TestSuite([dir_comp_suite,
                                 ])
  return alltests

if __name__ == "__main__":
  runner = unittest.TextTestRunner()
  sys.exit(not runner.run(testSuite()).wasSuccessful())
