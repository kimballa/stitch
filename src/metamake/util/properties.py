# (c) Copyright 2009 Cloudera, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
#
# @author aaron
#
# Python reader for properties files conforming to Java properties-file
# format. See http://java.sun.com/j2se/1.5.0/docs/api/java/util/Properties.html
# for the authoritative syntax.
#  The summary version:
#
#  - one property per line.
#  - blank lines, lines that start with '#' or '!' are ignored
#  - properties are written in one of the following forms:
#    -- "key = value", "key : value", or "key value" form.
#    -- the latter of these supports space, tab, or formfeed as the separator
#  - The "=" or ":" may or may not have surrounding whitespace
#  - whitespace around key and value names is trimmed and forgotten
#  - whitespace at beginning or end of a line is trimmed and forgotten
#  - \:, \=, \r, \n, \\ are all valid escape sequences
#  - undefined \X characters escape to themselves.
#  - values may be set to the empty string (e.g., "key = " or "key")
#  - A lone \ on the end of a line extends a value to the next line
#
# This actually extends java.util.properties in one way:
# we may want to load a set of paths in to the properties sheet. If
# there are paths in a properties file, we want those paths to be relative
# to the properties file location. But other properties set by the
# setProperty() method should be relative to the cwd. So we provide
# a directory name and a list of keys which have paths for values.
# these will be automatically normalized by the load() function.

import os

import metamake.util.output as output

class Properties(object):
  """ Works like java.util.Properties """

  def __init__(self):
    self.props = { }
    self.argParsers = []

  def clone(self):
    """ Returns a separate clone of the properties dictionary.
        ArgParsers are left behind."""
    newProps = Properties()
    for key in self.props.keys():
      newProps.props[key] = self.props[key]
    return newProps

  def getProperty(self, key, defaultVal=None):
    """ returns the property identified by key, or defaultVal if not found """
    try:
      return self.props[key]
    except KeyError:
      return defaultVal

  def getInt(self, key, defaultVal=None):
    try:
      return int(self.getProperty(key, None))
    except ValueError:
      return defaultVal
    except TypeError:
      return defaultVal


  def getBoolean(self, key, defaultVal=False):
    val = self.getProperty(key, None)

    ret = defaultVal
    if val == "true" or val == "True" or val == "yes" or val == "Yes" \
        or val == "on" or val == "On" or val == "":
      ret = True
    elif val == "false" or val == "False" or val == "no" or val == "No" \
        or val == "off" or val == "Off":
      ret = False

    return ret


  def forget(self, key):
    """ removes a key from the map if it exists """
    try:
      del(self.props[key])
    except KeyError:
      pass # ignore silently.

  def printTable(self, printLvl=output.DEBUG):
    """ Prints the properties to stdout """
    self.printDict(self.props)

  def printDict(self, dict, printLvl=output.DEBUG):
    for key in dict.keys():
      output.printlnLevel(printLvl, str(key) + " = " + str(dict[key]))

  def equalsDict(self, dict):
    """ return true if we contain the same key val pairs as 'dict'.
        Used mostly for unit testing. """
    return self.props == dict

  def load(self, handle, propPathRoot=None, pathKeyList=None):
    """ Reads key, val pairs from the file or other stream opened in handle.
        This augments existing properties already set """

    # states that our parser can be in.
    READING_KEY = 0
    READING_SEP = 1
    READING_VAL = 2

    def makePathsAbsolute(key, val):
      """ if the key is in pathKeyList, and the val is a relative
          path, it is relative to the propPathRoot. join them."""
      if propPathRoot != None and pathKeyList != None:
        try:
          pathKeyList.index(key)
          return os.path.join(propPathRoot, val)
        except ValueError:
          # not a path
          return val
      else:
        # we aren't normalizing paths; return unchanged
        return val


    def isWhitespace(ch):
      return ch == "\t" or ch == " " or ch == "\n" or ch == "\f" or ch == "\r"

    def isKeyChar(ch, escaped):
      """ is this character part of the key? or does it separate a key from
          its value """
      return escaped or (not isSepChar(ch, escaped))

    def isSepChar(ch, escaped):
      """ is this character part of the separator between key and val?"""
      return not escaped and (isWhitespace(ch) or ch == ':' or ch == '=')

    def resolveEscape(ch, escaped):
      """ what character do we output based on the current escape state? """
      if not escaped:
        return ch
      elif ch == "n":
        return "\n"
      elif ch == "r":
        return "\r"
      elif ch == "f":
        return "\f"
      elif ch == "t":
        return "\t"
      else:
        return ch # everything else escapes to itself

    # read in the file to parse line-wise
    lines = handle.readlines()

    # initial parser state: seeking the first key.
    readState = READING_KEY
    keypart = ""
    valpart = ""
    escaped = False

    for line in lines:
      line = line.lstrip() # trim leading whitespace
      if line.endswith("\n"): # remove any trailing newline
        line = line[:len(line)-1]

      if readState == READING_KEY:
        # we're looking for the start of the key
        if len(line) == 0:
          continue # ignore blank lines
        if line[0] == '#' or line[0] == '!':
          continue # ignore comment lines

      # read through the line; everything up to the first
      # separating character goes in the key part. Everything
      # after the initial separator goes in the val part

      for char in line:
        if readState == READING_KEY:
          if char == "\\" and not escaped:
            escaped = True
          elif isKeyChar(char, escaped):
            keypart = keypart + resolveEscape(char, escaped)
            escaped = False
          else:
            # we just found the start of the key-val separator
            readState = READING_SEP
        elif readState == READING_SEP:
          if isSepChar(char, escaped):
            pass # separator just gets ignored
          elif char == "\\":
            # first char in the value is escaped.
            escaped = True
            readState = READING_VAL
          else:
            # we've found the start of the value itself.
            valpart = valpart + resolveEscape(char, escaped)
            readState = READING_VAL
        elif readState == READING_VAL:
          if char == "\\" and not escaped:
            escaped = True
          else:
            valpart = valpart + resolveEscape(char, escaped)
            escaped = False

      # after reading all characters in the (trimmed) line...
      if escaped:
        # we ended the line with a "\"; so the following line is
        # also part of the key
        readState = READING_VAL
        escaped = False  # not actually escaped; just a terminating '\'
      else:
        valpart = makePathsAbsolute(keypart, valpart)

        # we've finished parsing this key val pair; insert it
        self.setProperty(keypart, valpart)

        # and reset to finding the start of the next key
        readState = READING_KEY
        keypart = ""
        valpart = ""


  def setProperty(self, key, value):
    self.props[key] = value

  def keys(self):
    return self.props.keys()

  # We delegate parsing of args to ArgParser instances. Each of these
  # has a map from --flag -> property name, and a map from environment
  # variables to property name. We run them in the order they're added
  # (so later ones can override earlier ones)

  # Note that we fulfill ArgParser's interface.

  def addArgParser(self, argParser):
    """ adds another argument parser to the chain """
    self.argParsers.append(argParser)

    # and notify the arg parser that it should populate this Properties.
    argParser.setTargetProperties(self)

  def parseArgs(self, argv):
    """ parse the command line arguments with all attached parsers.
        This should not include the program name (sys.argv[0]) """

    for argParser in self.argParsers:
      argParser.parseArgs(argv)

  def loadFromEnvironment(self):
    """ load relevant environment variables from all attached parsers """
    for argParser in self.argParsers:
      argParser.loadFromEnvironment()

  def printUsage(self):
    """ print the dictionary of command-line arguments we support """
    for argParser in self.argParsers:
      argParser.printUsage()

  def usesFlag(self, arg):
    """ return true if this properties file will consume a given command
        line flag """

    lastCount = None
    satisfiedBySomeone = False
    for argParser in self.argParsers:
      thisCount = argParser.usesFlag(arg)
      if lastCount != None and thisCount != lastCount and thisCount != 0:
        output.printlnError("Error: Ambiguous parse for argument " + arg)
        return 0
      if thisCount != 0:
        satisfiedBySomeone = True
        lastCount = thisCount
    if not satisfiedBySomeone:
      output.printlnError("Error: unsupported argument " + arg)
      return 0
    else:
      return lastCount

  def usesAllFlags(self, argv):
    """ return true if we can process all of argv """

    i = 0
    ret = True
    while i < len(argv):
      arg = argv[i]
      thisCount = self.usesFlag(arg)

      if thisCount == 0: # parsing this arg failed
        thisCount = 1
        ret = False

      # advance past the flag and any of its args
      i = i + thisCount

    return ret


