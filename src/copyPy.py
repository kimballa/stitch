#!/usr/bin/python
#
# (c) Copyright 2009 Cloudera, Inc.
#
# This is a small bootstrap script that copies
# all the python code from one python project
# into the python bin dir. This stage is executed
# before the makePy script walks through and actually
# compiles them.
#
# Usage:
# copyPy.py (projdir) (target)
#
# copies ${projdir}/** to ${target}, (which is normally
# bin/python/) and then cmopiles all the source available.
#
# The ${projName} layer of the directory is
# excised so that all the packages line up
# on top of one another.
#
# IMPORTANT: This single .py file is copied by the build
# script into the bin directory and executed from there. It must
# be COMPLETELY SELF-HOSTING -- no dependencies on anything
# else in the build tree!

import os
import py_compile
import shutil
import stat
import sys

if len(sys.argv) < 3:
  print "Usage: copyPy.py (srcdir) (targetdir)"
  sys.exit(1)

srcdir = sys.argv[1]
targetdir = sys.argv[2]
numCopied = 0
exitStatus = 0

# code clone from stitch.util.dirutil
# put here because we need to self-host this file.
def mkdirRecursive(newdir):
  """works the way a good mkdir should :)
      - already exists, silently complete
      - regular file in the way, raise an exception
      - parent directory(ies) does not exist, make them as well
  """
  if os.path.isdir(newdir):
    pass
  elif os.path.isfile(newdir):
    raise OSError("a file with the same name as the desired " \
                  "dir, '%s', already exists." % newdir)
  else:
    head, tail = os.path.split(newdir)
    if head and not os.path.isdir(head):
      mkdirRecursive(head)
    #print "_mkdir %s" % repr(newdir)
    if tail:
      os.mkdir(newdir)

def copyChildren(root, target):
  """ recursively copies .py files in root/* to target/ """
  global numCopied, exitStatus

  if not os.path.exists(target):
    mkdirRecursive(target)
  childList = os.listdir(root)
  for entry in childList:
    source = root + os.sep + entry
    if os.path.isfile(source) and entry.endswith(".py"):
      doCopy = True
      if os.path.exists(target + os.sep + entry):
        srcStat = os.stat(source)
        targetStat = os.stat(target + os.sep + entry)
        if srcStat[stat.ST_MTIME] <= targetStat[stat.ST_MTIME]:
          doCopy = False # target is same or newer
        else:
          os.remove(target + os.sep + entry)
      if doCopy:
        shutil.copy2(source, target)
        shutil.copymode(source, target + os.sep + entry)
        numCopied = numCopied + 1
    elif os.path.isdir(source):
      # make the child directory in the target tree,
      # if it doesn't already exist
      if not os.path.exists(target + os.sep + entry):
        mkdirRecursive(target + os.sep + entry)
      # and then copy all of its children
      copyChildren(root + os.sep + entry, target + "/" + entry)



if os.path.isdir(srcdir):
  while srcdir.endswith(os.sep):
    srcdir = srcdir[:len(srcdir)-1]
  base = os.path.basename(srcdir)
  copyChildren(srcdir, targetdir + os.sep + base)
else:
  # it's actually just a single file
  sourceFile = srcdir
  doCopy = True
  if os.path.isdir(targetdir):
    target = targetdir + os.sep + os.path.basename(sourceFile)
  else:
    target = targetdir

  if os.path.exists(target):
    srcStat = os.stat(sourceFile)
    targetStat = os.stat(target)
    if srcStat[stat.ST_MTIME] <= targetStat[stat.ST_MTIME]:
      doCopy = False # target is same or newer
    else:
      os.remove(target)
  if doCopy:
    shutil.copy2(sourceFile, target)
    shutil.copymode(sourceFile, target)
    numCopied = 1


suffix = "s."
if numCopied == 1:
  suffix = "."

if numCopied > 0:
  print "Copied", numCopied, "file" + suffix
sys.exit(exitStatus)


