#
# (c) Copyright 2009 Cloudera, Inc.
#
#
# BuildFile:
# An object that reads a build file and its information
#

import stitch.paths as paths

import os

# build files are called this in every directory.
DEFAULT_BUILD_FILENAME = "targets"


# targets within a file are identified after this character
SUBTARGET_SPECIFIER = ":"

# and the "safe name" of a target is specified after this character
SAFE_SEPARATOR = "."

# the current build file object being processed by the
# loop. Note that doing this in a global variable restricts
# the system to a single thread.
curBuildFile = None

def getCurBuildFile():
  """ return the current buildfile object being processed """
  global curBuildFile
  return curBuildFile


def setCurBuildFile(buildfile):
  global curBuildFile
  curBuildFile = buildfile



class BuildFile(object):
  """ An object that represents the information stored in
      a single BUILD file """

  def __init__(self, path):
    # the actual path to the file to open
    self.path = os.path.abspath(path)
    if os.path.isdir(self.path) or self.path.endswith(os.sep):
      self.path = os.path.abspath(self.path
          + os.sep + DEFAULT_BUILD_FILENAME)

    # the pathname relative to the build root.
    self.canonicalName = paths.getCanonicalName(path)
    self.safeName = paths.getSafeName(path)

    self.targets = []
    self.defaultTarget = None
    self.execute()


  def getBuildFileDirectory(self):
    """ return the directory containing the buildfile """
    # the canonical name starts with the root qualifier; chop that off.
    return self.canonicalName[len(paths.ROOT_QUALIFIER):]

  def getCanonicalName(self):
    """ returns the path component we give to all
        targets in this buildfile """
    return self.canonicalName

  def getFileName(self):
    """ Returns the filename for this build file """
    return self.path

  def execute(self):
    """ Load the Targets file by running it in the context
        of the current module. """
    import stitch.targets.alltargets as alltargets

    setCurBuildFile(self)

    handle = None
    try:
      try:
        handle = open(self.path)
        scriptSource = handle.read()
      except IOError, ioe:
        print "Error: Buildfile " + self.path + " could not be loaded."
        print ioe
        return
    finally:
      if handle != None:
        handle.close()

    try:
      code = compile(scriptSource, self.path, 'exec')
    except SyntaxError, se:
      print "Syntax error evaluating " + self.path + ":"
      print se
      return

    # set up environment in which to execute the script
    globals = {}
    locals = {}

    # put the elements of the targets module in their
    # environment
    for obj in dir(alltargets):
      if not obj.startswith("__"):
        globals[obj] = getattr(alltargets, obj)

    # run the user's Targets file. The objects created and named will
    # be stored in the 'locals' dict for us to extract from later
    exec code in globals, locals

    self.userObjects = locals

    # objects currently have "__anonymous" names. put our own
    # canonical name ahead of these.
    for target in self.targets:
      target.setCanonicalName(self.canonicalName + SUBTARGET_SPECIFIER + target.getCanonicalName(),
          True)
      target.setSafeName(self.safeName + SAFE_SEPARATOR + target.getSafeName())

    # assign the names of the named user objects back to themselves
    for obj in self.userObjects:
      if isinstance(self.userObjects[obj], alltargets.Target):
        self.userObjects[obj].setCanonicalName(self.canonicalName
            + SUBTARGET_SPECIFIER + obj, False)
        self.userObjects[obj].setSafeName(self.safeName + SAFE_SEPARATOR + obj)

    # and assign the build file's root name to the default target
    if None != self.defaultTarget:
      self.defaultTarget.setCanonicalName(self.canonicalName, False)
      self.defaultTarget.setSafeName(self.safeName)


  def addTarget(self, someTarget):
    """ registers a target created in this build file. This
        is a callback function used by the Targets script"""
    import stitch.targets.alltargets as alltargets
    if not isinstance(someTarget, alltargets.Target):
      raise Exception(str(someTarget) + " is not a Target")

    self.targets.append(someTarget)
    if self.defaultTarget == None:
      self.defaultTarget = someTarget


  def getRequiredBuildFiles(self):
    """ return a list of paths to BuildFiles which were
        referenced by targets in this BuildFile """

    out = []
    for target in self.targets:
      reqs = target.required_targets
      if None != reqs:
        for req in reqs:
          # chop off target name within file
          splitPos = req.find(SUBTARGET_SPECIFIER)
          if -1 != splitPos:
            req = req[0:splitPos]
          # If the req name is absolute (starts with '//'), then we chomp the leading
          # qualifier and return it as-is. Otherwise we join with the current
          # buildfile directory.
          if req.startswith(paths.ROOT_QUALIFIER):
            req = req[len(paths.ROOT_QUALIFIER):]
          else:
            req = os.path.normpath(os.path.join(self.getBuildFileDirectory(), req))

          # Test to see if the file exists; give an error if not.
          actual_file_name = os.path.join(req, DEFAULT_BUILD_FILENAME)
          if not os.path.exists(actual_file_name):
            raise Exception("Target " + target.getCanonicalName() \
                + " references missing buildfile " + actual_file_name)

          out.append(req)

    return out


  def getTargets(self):
    """ return all the targets defined in this buildfile """
    return self.targets

