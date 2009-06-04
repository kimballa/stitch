#
# (c) Copyright 2009 Cloudera, Inc.
#
#
# BuildFile:
# An object that reads a build file and its information
#

import stitch.paths as paths
import stitch.propstack as propstack

import os
import sys

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


# Starts as None; turns into a list populated only after a get_extensions()
# is performed and that calls load_extensions() in turn.
__extension_objs = None


def get_globals(with_exts=False):
  """ Return a dictionary to use as the 'globals' environment dict for
      importing a module or executing a script/targets file
  """
  import stitch.targets.alltargets as alltargets

  globals = {}

  # put the elements of the alltargets module in their environment.
  for obj in dir(alltargets):
    if not obj.startswith("__"):
      globals[obj] = getattr(alltargets, obj)

  if with_exts:
    # put the handles to the extension modules in their environment.
    globals.update(get_extensions())

  return globals


def load_extensions():
  """ If there's a stitch-ext/ dir in the root of the build tree, load any
      python files from there as modules and retain their environments to
      load into all targets files we process.
  """
  global __extension_objs

  # Clear existing extensions
  __extension_objs = {}

  props = propstack.get_properties()
  ext_dir = props.getProperty("stitch-extensions")
  if ext_dir == None:
    return # no work to do.

  if not os.path.exists(ext_dir):
    return # no extensions in this project.

  # Add the extension dir as a module import source
  old_sys_path = sys.path
  sys.path.append(ext_dir)

  try:
    # import all those files as modules
    files = os.listdir(ext_dir)
    for file in files:
      if file.endswith(".py"):
        modname = file[:-3] # chop of the extension to get module name
        # Load and execute this module, and incorporate its env dictionary
        # into the master extension dictionary
        print "Loading module:", modname
        mod = __import__(modname)
        __extension_objs[modname] = mod
  finally:
    # restore the configured sys.path
    sys.path = old_sys_path


def get_extensions():
  """ return the environment dictionary constructed from the user extensions """
  global __extension_objs

  if __extension_objs == None:
    load_extensions()
  return __extension_objs


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

  def exec_for_env(self, filename, with_exts=False):
    """ Load a python file and execute it, returning a dictionary of all the public
        objects in their output environment.
    """
    handle = None
    try:
      try:
        handle = open(filename)
        scriptSource = handle.read()
      except IOError, ioe:
        print "Error: File " + filename + " could not be loaded."
        print ioe
        return {}
    finally:
      if handle != None:
        handle.close()

    try:
      code = compile(scriptSource, filename, 'exec')
    except SyntaxError, se:
      print "Syntax error evaluating " + filename + ":"
      print se
      return {}

    # set up environment in which to execute the script
    globals = get_globals(with_exts)
    locals = {}

    # run the user's code. The objects created and named will
    # be stored in the 'locals' dict for us to extract from.
    exec code in globals, locals

    public_objs = {}
    for obj in locals:
      if not obj.startswith("__"):
        public_objs[obj] = locals[obj]
    
    return public_objs

  def execute(self):
    """ Load the Targets file by running it in the context
        of the current module. """

    import stitch.targets.alltargets as alltargets

    setCurBuildFile(self)

    self.userObjects = self.exec_for_env(self.path, with_exts=True)

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

