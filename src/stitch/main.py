# (c) Copyright 2009 Cloudera, Inc.
#
# stitch [--generator GeneratorName ]
#
# Starts in the current directory looking for "Targets"
# files. Recursively explores to create the build
# system targets.
#
# Multiple generators:
# By default, stitch will use the BuildGenerator to create a
# build script to build your workspace.
# You can pick a generator with --generator GeneratorName or
# -g GeneratorName. If this is a fully-qualified name, it will
# load it out of the provided package. Otherwise, it assumes it
# is in stitch.allgenerators. You can list the public
# generators available in this package with --list.
#
#

import os
import sys

import stitch.buildfile as buildfile
from stitch.buildgenerator import BuildGenerator
import stitch.allgenerators as allgenerators
import stitch.signore as signore
import stitch.paths as paths
import stitch.propstack as propstack

############## some helper functions ####################

def listGenerators():
  """ list the public contents of Generators package """
  for name in dir(allgenerators):
    generatorClass = getattr(allgenerators, name)
    if hasattr(generatorClass, "isPublic"):
      # construct one of these
      gen = generatorClass()
      if gen.isPublic():
        print gen.getDescription()

def printUsage():
  """ print usage """

  print """Usage: stitch [arguments]

  With no arguments, runs the default generator to create a build script
  to build the source tree.

  Arguments:
    -C (dir)                     Switch to (dir) before starting work.
    --help                       Print this usage info and exit
    --list                       List available generators and exit
    --generator generatorName    Run stitch with this generator. This
      (or -g)                    can be an output of --list or a fully-
                                 qualified class name that implements
                                 stitch.generator.Generator.
                                 Only the last value of -g is used.
"""

def loadGenerator(generatorName):
  """ Return the class object representing the named generator """
  print "Loading generator:", generatorName

  if generatorName.find(".") > -1:
    # this is a fully-specified class name. Load it
    lastDot = generatorName.rfind(".")
    package = generatorName[0:lastDot]
    className = generatorName[lastDot+1:]

    module = __import__(package, globals(), {}, [className], -1)
    return getattr(module, className)
  else:
    # load something out of our own generators package
    generatorClass = getattr(allgenerators, generatorName, None)
    if generatorClass == None:
      print "Error: No such generator", generatorName
      sys.exit(1)
    elif hasattr(generatorClass, "isPublic"):
      # looks like a generator to me. We don't actually care if it's
      # public here; that's just a test to see if it is somewhat sane
      # of a Generator implementation. Just return the class obj
      return generatorClass
    else:
      print "Error: No such generator", generatorName
      sys.exit(1)



def main(argv):
  # by default, use the BuildGenerator
  userGenerator = BuildGenerator

  if len(argv) > 0:
    i = 1
    while i < len(argv):
      if argv[i] == "--list":
        listGenerators()
        return 0
      elif argv[i] == "-C":
        if i == len(argv) -1:
          print "Error: directory name required. See --help for usage."
          return 1
        i = i + 1
        os.chdir(argv[i])
      elif argv[i] == "--help":
        printUsage()
        return 0
      elif argv[i] == "--executable":
        if i == len(argv) - 1:
          print "Error: executable name required."
          return 1
        i = i + 1
        propstack.set_bin_dir_by_executable(argv[i])
      elif argv[i] == "-g" or argv[i] == "--generator":
        if i == len(argv) - 1:
          print "Error: generator name required. See --help for usage."
          return 1
        i = i + 1
        userGenerator = loadGenerator(argv[i])
      i = i + 1

  paths.setBuildRoot(os.getcwd())

  # start out by processing the current directory.
  filesToProcess = [os.getcwd()]
  initialBuildRoot = paths.getFullBuildFilePath(".")
  realPathToBuildRoot = os.path.realpath(initialBuildRoot)
  filesSeen = [ initialBuildRoot, realPathToBuildRoot]

  buildFileObjects = []
  allTargets = []

  # read in all the BuildFile objects

  while len(filesToProcess) > 0:
    nextBatch = [] # next BFS frontier
    for file in filesToProcess:
      # first check to make sure this isn't in an ignore list.
      signore.loadThroughPath(file)
      ignoreFilePath = signore.shouldIgnorePath(file)
      if ignoreFilePath != None:
        # don't do anything more for this buildfile
        print "s-ignoring", file, "(" + ignoreFilePath + ")"
        continue

      # process the file
      print "Processing", file

      bf = buildfile.BuildFile(file)
      buildFileObjects.append(bf)

      # now get the next list of targets to add
      # to the following bfs generation
      newTargets = bf.getRequiredBuildFiles()
      for newTarget in newTargets:
        newTarget = paths.getFullBuildFilePath(newTarget)
        realPathToNewTarget = os.path.realpath(newTarget)

        # is the user-specified path one we've processed?
        try:
          filesSeen.index(newTarget)
        except ValueError:
          # no. What about its realpath (symlinks resolved)?
          try:
            filesSeen.index(realPathToNewTarget)
          except ValueError:
             # this is a genuine new target
            nextBatch.append(newTarget)

          # make sure we don't visit it twice
          filesSeen.append(newTarget)
          filesSeen.append(realPathToNewTarget)
    filesToProcess = nextBatch

  # get the list of Target objects
  for buildFile in buildFileObjects:
    allTargets.extend(buildFile.getTargets())

  gen = userGenerator()
  gen.generate(allTargets)

  return 0

if __name__ == "__main__":
  ret = main(sys.argv)
  sys.exit(ret)


