# (c) Copyright 2009 Cloudera, Inc.
#
# mmignore:  A module that allows ignoring of directories in the
# build process.
#
# Each time metamake encounters a new directory, it first looks for
# a .mmignore file before it looks for the Targets file in that
# directory.
#
# The .mmignore file may contain a list of relative paths:
#  ".", "./foo", "foo", etc
#
# Comment lines are those which begin with "#" or "!"
# Blank lines and comment lines are ignored.
#
# All of these paths are relative to the location of the .mmignore
# file. Any paths in this directory -- and their subpaths -- are all
# ignored by metamake.
#
# Note that this overrides any actual dependencies discovered in "valid"
# Targets files. So you can metamake yourself a broken build if you
# .mmignore a directory that you need.
#
# .mmignore is a convenience to allow you to disable parts of the build
# that are not relevant to your own work. HOWEVER, all parts of the build
# must be included in the "real" build. So .mmignore files are ignored
# by git by default. Do not add a .mmignore file to the official versioned
# tree unless you are disabling a directory that everyone agrees is dead
# code and fully deprecated.

import os

import metamake.paths as paths


allIgnoreFiles = {}

def loadThroughPath(path):
  """ recursively loads mmignore files in 'path' and all parent
      directories of 'path' up to (and including) the build root.
      This will not load mmignore files from directories outside
      the buildroot. """

  global allIgnoreFiles

  buildRoot = paths.getBuildRoot()
  absBuildRoot = os.path.abspath(buildRoot)

  thisPath = os.path.abspath(path)
  while os.path.commonprefix([thisPath, absBuildRoot]) == absBuildRoot:

    try:
      # test: did we already parse this one?
      allIgnoreFiles[thisPath]
    except KeyError:
      # nope; parse it and add to the map.
      allIgnoreFiles[thisPath] = MMIgnore(thisPath)

    # go up one level.
    thisPath = os.path.abspath(thisPath + os.sep + "..")


def shouldIgnorePath(path):
  """ return the path to the mmignore file that contains
      'path', or None if we don't ignore the input path. """

  global allIgnoreFiles

  for key in allIgnoreFiles.keys():
    mmi = allIgnoreFiles[key]
    if mmi.ignorePath(path):
      return mmi.getFilename()

  return None


class MMIgnore(object):
  """ metamake ignore file. Don't instantiate this directly yourself;
      use mmignore.loadThroughPath() to load
      and mmignore.shouldIgnorePath() to test
  """

  def __init__(self, path):
    self.ignorePaths = []
    self.mmiFilename = None
    self.load(path)

  def getFilename(self):
    return self.mmiFilename

  def load(self, path):
    """ read a .mmignore file """

    if os.path.isdir(path):
      # this is just a directory. tack on the suffix.
      filename = path + os.sep + ".mmignore"
    else:
      filename = path

    basePath = os.path.realpath(os.path.dirname(filename))
    self.mmiFilename = filename

    if not os.path.exists(filename):
      # nothing to load here.
      return

    handle = open(filename)
    lines = handle.readlines()
    for line in lines:
      line = line.strip()
      if line.startswith("#") or line.startswith("!") or len(line) == 0:
        # ignore comments and blank lines
        continue
      self.ignorePaths.append(os.path.realpath(os.path.join(basePath, line)))

    handle.close()


  def ignorePath(self, testPath):
    """ return True if pathName is a directory that should be ignored
        because of this .mmignore file. """

    realTestPath = os.path.realpath(testPath)
    for path in self.ignorePaths:
      if realTestPath.startswith(path):
        return True

    return False

