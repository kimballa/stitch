# (c) Copyright 2009 Cloudera, Inc.
#
# Unit test cases for PackageTarget and Steps

import stitch.steps.filesteps as filesteps
from   stitch.testutil.asserts import TestCaseWithAsserts

class CopyDirTest(TestCaseWithAsserts):

  def setUp(self):
    # clear the static component before each test.
    filesteps.CopyDir.clear_excludes_for_test()


  def test_single_global_exclude(self):
    filesteps.CopyDir.always_exclude("foo")
    self.assertEquals(filesteps.CopyDir.get_permanent_excludes(), [ "foo" ])

  def test_redundant_global_exclude(self):
    filesteps.CopyDir.always_exclude("foo")
    filesteps.CopyDir.always_exclude("foo")
    self.assertEquals(filesteps.CopyDir.get_permanent_excludes(), [ "foo" ])

  def test_multi_global_exclude(self):
    filesteps.CopyDir.always_exclude("foo")
    filesteps.CopyDir.always_exclude("bar")

    excludes = filesteps.CopyDir.get_permanent_excludes()
    try:
      excludes.index("foo")
      excludes.index("bar")
    except ValueError:
      self.fail("Could not find expected exclusion rule")

    try:
      excludes.index("baz")
      self.fail("Found unexpected exclusion rule")
    except ValueError:
      # This is expected; we never excluded baz.
      pass

    self.assertEquals(len(excludes), 2)



if __name__ == '__main__':
  unittest.main()

