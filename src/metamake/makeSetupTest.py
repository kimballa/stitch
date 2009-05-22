#!/usr/bin/env python
# (c) Copyright 2009 Cloudera, Inc.
#
# Unit test cases for makeSetup.py
#
# This is invoked by alltests.py, which is invoked by metamake:
#  $ cd $GIT
#  $ bin/python/metamake
#  $ ./build --phase test python/Build/:metamake_pyunit

import os
import unittest
import shutil
import sys
import tempfile

import makeSetup

class MakeSetupTest(unittest.TestCase):
  def tearDown(self):
    try:
      os.remove(self.tmp_file)
    except:
      pass

  def write_file(self, contents):
    (_, path) = tempfile.mkstemp()
    handle = open(path, 'w')
    handle.write(contents)
    handle.close()
    self.tmp_file = path
    return path

  def test_datafiles_map(self):
    good = self.write_file("srcFile1\tdestDir1\nsrcFile2\tdestDir2")
    map = makeSetup.datafiles_map(good, "")
    self.assertEquals("destDir1", map.get("srcFile1"))
    self.assertEquals("destDir2", map.get("srcFile2"))

    bad = "srcFile1\tdestDir1,srcFile1\tdestDir1"
    self.assertRaises(Exception, makeSetup.datafiles_map, [bad])

  def test_datafiles_str_outmap(self):
    good = self.write_file("srcFile1\tdestDir1\nsrcFile2\tdestDir2")
    expected = { 'destDir1' : ['srcFile1'],
                 'destDir2' : ['srcFile2']
               }
    self.assertEquals(expected, makeSetup.datafiles_str_map(good, ""))

  def test_recursive_datafiles(self):
    tmp_dir_name = tempfile.mkdtemp()
    try:
      os.mkdir(os.path.join(tmp_dir_name,"a"))
      os.mkdir(os.path.join(tmp_dir_name,"b"))

      # note: empty dirs aren't sent to the client.
      os.mkdir(os.path.join(tmp_dir_name,"empty-on-purpose"))

      h = open(os.path.join(tmp_dir_name, "a", "file1"), "w")
      h.close()

      h = open(os.path.join(tmp_dir_name, "b", "file2"), "w")
      h = open(os.path.join(tmp_dir_name, "b", "file3"), "w")
      h.close()

      os.mkdir(os.path.join(tmp_dir_name, "a", "subdir"))
      h = open(os.path.join(tmp_dir_name, "a", "subdir", "subfile"), "w")
      h.close()

      input = self.write_file(tmp_dir_name + "/**\tdestdir\nfoo\tbar")

      src_a = os.path.join(tmp_dir_name, "a")
      src_a_sub = os.path.join(tmp_dir_name, "a", "subdir")
      src_b = os.path.join(tmp_dir_name, "b")

      expected = { "destdir/a" : [ os.path.join(src_a, "file1") ],
                   "destdir/a/subdir" : [ os.path.join(src_a_sub, "subfile") ],
                   "bar" : [ "foo" ],
                   "destdir/b" : [ os.path.join(src_b, "file2"), os.path.join(src_b, "file3") ]
                 }
      self.assertEquals(expected, makeSetup.datafiles_str_map(input, ""))
    finally:
      shutil.rmtree(tmp_dir_name)


if __name__ == '__main__':
  unittest.main()
