# (c) Copyright 2009 Cloudera, Inc.

"""
  There are a set of well-defined properties files that govern
  metamake's behavior; these are read as Java properties files
  with "ant" style semantics that once a property is set, it
  is immutable.

  We read, in order:
    ./my.properties
    ./build.properties
    /etc/metamake/metamake-config.properties

  This module returns a parsed AntProperties object that contains
  results from all these files.
"""

import metamake.util.antproperties as antproperties

__internal_properties = None

def get_properties():
  global __internal_properties

  if __internal_properties == None:
    __internal_properties = antproperties.AntProperties()

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
      h = open("/etc/metamake/metamake-config.properties")
      __internal_properties.load(h)
      h.close()
    except IOError:
      print "Warning: Could not load /etc/metamake/metamake-config.properties"

  return __internal_properties

