#
# (c) Copyright 2009 Cloudera, Inc.
#
#
# paths: methods that manipulate paths to buildfiles
#

import os

# paths relative to the mmroot start with '//'
ROOT_QUALIFIER = os.sep + os.sep

# paths relative to a target's output directory start with '$/'
OUTDIR_QUALIFIER = '$' + os.sep

def is_root_qualified(path):
  """ Return true if the provided path starts with the mmroot qualifier """
  return path.startswith(ROOT_QUALIFIER)

def is_outdir_qualified(path):
  """ Return true if the provided path starts with the outdir qualifier """
  return path.startswith(OUTDIR_QUALIFIER)

def dequalify(path):
  """ Strip any leading path qualifier from the provided path """
  if is_root_qualified(path):
    return path[len(ROOT_QUALIFIER):]
  elif is_outdir_qualified(path):
    return path[len(OUTDIR_QUALIFIER):]
  else:
    return path

buildRoot = os.path.abspath(os.getcwd())
def setBuildRoot(root):
  global buildRoot
  buildRoot = os.path.abspath(root)

def getBuildRoot():
  global buildRoot
  return buildRoot

def getFullBuildFilePath(partialPath):
  """ return the full path to a build file. The dependencies
      themselves are relative to the root in which metamake
      was started. This returns the path attached to the
      buildroot, in an absolute, canonicalized form """
  return os.path.abspath(os.path.join(getBuildRoot(), partialPath))

def getRelativeBuildFilePath(path):
  """ return the directory containing the current build file,
      relative to the BuildRoot. If the target is not a subdirectory
      of the buildroot, returns the whole path.
      targets that are not subdirectories of the buildroot. """

  # normalize everything
  buildRoot = getBuildRoot()
  fullPath = os.path.realpath(path) # changed from abspath; resolves symlinks

  # if there's a common prefix with the buildroot, chop it off.
  common = os.path.commonprefix([buildRoot, fullPath])
  if common != buildRoot:
    common = "" # not the buildroot itself; use full path.

  if len(common) > 0 and not common.endswith(os.sep):
    common = common + os.sep

  # get the relative entry
  relative = fullPath[len(common):]

  # remove the name of the Targets file if it was added
  if os.path.isfile(relative):
    relative = os.path.dirname(relative)

  return relative


def getCanonicalName(path):
  """ Return the translated name from path elements to the
      canonicalized target name which appears in other
      Targets files """
  relative = getRelativeBuildFilePath(path)
  return ROOT_QUALIFIER + relative


def getSafeName(path):
  """ Return the translated name from path elements to
      a canonicalized target name which can be put into
      ant build files, etc. """

  relative = getRelativeBuildFilePath(path)
  return relative.replace(os.sep, ".")


