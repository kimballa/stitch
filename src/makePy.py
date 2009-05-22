#!/usr/bin/python
#
# (c) Copyright 2009 Cloudera, Inc.
#
#
#
# IMPORTANT: This single .py file is copied by the build
# script into the bin directory and executed from there. It must
# be COMPLETELY SELF-HOSTING -- no dependencies on anything
# else in the build tree!

"""
  This is a small bootstrap script that compiles all
  .py files in bin/python to .pyc files (thus checking
  for errors before we run any of it)

  Usage:
  makePy.py (target)
"""

import os
import py_compile
import shutil
import stat
import sys

if len(sys.argv) < 2:
  print "Usage: makePy.py (targetdir)"
  sys.exit(1)

targetdir = sys.argv[1]
numCompiled = 0
globalError = False

def compilePyVisitor(arg, dirName, entries):
  """ visitor function for os.path.walk; compiles .py
      files it discovers."""
  global globalError
  global numCompiled

  for entry in entries:
    fullEntry  = dirName + os.sep + entry
    if fullEntry.endswith(".py"):
      compile = True
      if os.path.exists(fullEntry + "c"):
        # check to see if .pyc is newer.
        pycTime = os.stat(fullEntry + "c").st_mtime
        pyTime = os.stat(fullEntry).st_mtime
        if (pyTime < pycTime):
          compile = False # pyc is newer
      elif os.path.exists(fullEntry + "o"):
        # check to see if .pyo is newer
        pyoTime = os.stat(fullEntry + "o").st_mtime
        pyTime = os.stat(fullEntry).st_mtime
        if (pyTime < pyoTime):
          compile = False # pyo is newer
      if compile:
        try:
          py_compile.compile(fullEntry, doraise=True)
        except py_compile.PyCompileError, pce:
          print "Error compiling " + fullEntry + ":"
          print pce
          globalError = True
        numCompiled = numCompiled + 1



os.path.walk(targetdir, compilePyVisitor, None)

suffix = "s."
if numCompiled == 1:
  suffix = "."

if globalError:
  print "Errors found when compiling", numCompiled, "file" + suffix
  sys.exit(1)
else:
  if numCompiled > 0:
    print "Successfully compiled", numCompiled, "new/updated file" + suffix


