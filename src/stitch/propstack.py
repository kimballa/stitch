# (c) Copyright 2009 Cloudera, Inc.

"""
  There are a set of well-defined properties files that govern
  stitch's behavior; these are read as Java properties files
  with "ant" style semantics that once a property is set, it
  is immutable.

  We read, in order:
    ./my.properties
    ./build.properties
    /etc/stitch/stitch-config.properties

  This module returns a parsed AntProperties object that contains
  results from all these files.
"""

import os
import sys

import stitch.util.antproperties as antproperties

__internal_properties = None
__stitch_bin_dir = None


def set_bin_dir_by_executable(executable):
  global __stitch_bin_dir

  real_executable = os.path.realpath(executable)
  real_bin_dir = os.path.dirname(real_executable)
  __stitch_bin_dir = real_bin_dir


def get_stitch_home():
  global __stitch_bin_dir

  if __stitch_bin_dir == None:
    __stitch_bin_dir = os.path.realpath(sys.argv[0])
  stitch_home = os.path.join(__stitch_bin_dir, "..")
  return os.path.abspath(stitch_home)


def get_properties():
  global __internal_properties

  if __internal_properties == None:
    __internal_properties = antproperties.AntProperties()

    # Set the basedir first.
    __internal_properties.setProperty("basedir", os.path.abspath(os.getcwd()))

    stitch_home = get_stitch_home()

    try:
      h = open("my.properties")
      __internal_properties.load(h)
      h.close()
    except IOError:
      pass # Couldn't read from my.properties; silently ignore it.

    try:
      h = open("build.properties")
      __internal_properties.load(h)
      h.close()
    except IOError:
      pass # Couldn't read from build.properties; silently ignore it.

    try:
      h = open(os.path.join(stitch_home, "etc/stitch-config.properties"))
      __internal_properties.load(h)
      h.close()
    except IOError:
      print "Warning: Could not load " + os.path.join(stitch_home, "etc/stitch-config.properties")

  return __internal_properties

