#
# (c) Copyright 2009 Cloudera, Inc.
#
# methods centered on running the top-level build script
#
#

import os

import metamakelib.util.oldshell as shell

class BuildError(Exception):
  " Errors when running a build cmd "
  def __init__(self, value):
    self.value = value

  def __str__(self):
    return repr(self.value)


cachedBuildRoot = None
def getBuildRoot(forceReload=False):
  """ return the root directory where build script can be found. """

  global cachedBuildRoot

  if cachedBuildRoot != None and not forceReload:
    return cachedBuildRoot

  prevcwd = None
  curcwd = os.getcwd()

  while prevcwd == None or prevcwd != curcwd:
    if not curcwd.endswith(os.sep):
      curcwd = curcwd + os.sep

    build_file = curcwd + build
    if os.path.isfile(build_file):
      cachedBuildRoot = curcwd
      return cachedBuildRoot


    prevcwd = curcwd
    curcwd = os.path.abspath(curcwd + "..")

  # couldn't find it
  cachedBuildRoot = None
  return None

def hasBuildFile(somePath):
  """ return True if build is present in somePath """
  if not somePath.endswith(os.sep):
    somePath = somePath + os.sep

  return os.path.exists(somePath + "build")


def buildTask(task, flags):
  """ run build task, and return the exit status
      Note that this changes the cwd, so is not thread safe.
  """

  buildRoot = getBuildRoot()
  initialCwd = os.getcwd()
  if None == buildRoot:
    raise BuildError("No buildroot could be found starting at " + initialCwd)

  try:
    os.chdir(buildRoot)
    try:
      shell.sh(buildRoot + os.sep + "build " + task, flags)
    except shell.CommandError, ce:
      raise BuildError("Result code " + str(ce.value) + " when running task " \
          + str(task))
  finally:
    os.chdir(initialCwd)


def metaMake(srcRoot, flags):
  """ run the metamake program to generate the build file. """

  initialCwd = os.getcwd()
  try:
    os.chdir(srcRoot)
    try:
      shell.sh("./bin/python/metamake", flags)
    except shell.CommandError, ce:
      raise BuildError("metamake exited with status " + str(ce.value))
  finally:
    os.chdir(initialCwd)


def clean(flags):
  return buildTask("clean", flags)

def build(flags):
  return buildTask("build", flags)

def test(flags):
  return buildTask("test", flags)


