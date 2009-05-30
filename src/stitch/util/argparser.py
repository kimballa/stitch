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
# @author aaron

import os

class ArgParser(object):
  def __init__(self, argMap, boolTrues=[], boolFalses=[], envMap={}):
    self.argVarMap = argMap
    self.boolTrues = boolTrues
    self.boolFalses = boolFalses
    self.envVarMap = envMap
    self.targetProps = None
    self.stopSymbol = None

  def setStopSymbol(self, stop):
    """ if this flag is encountered, we immediately cease arg parsing """
    self.stopSymbol = stop

  def setTargetProperties(self, props):
    """ determines which properties object we're attached to """
    self.targetProps = props

  def parseArgs(self, argList):
    """ read command-line arguments and update the properties from there"""

    if self.targetProps == None:
      raise Exception("ArgParser not attached to Properties")

    i = 0
    while i < len(argList):
      flag = argList[i]

      if flag == self.stopSymbol:
        # no more arguments for us to parse.
        break

      # what property are we setting?
      try:
        prop = self.argVarMap[flag]
      except KeyError:
        # This is not a flag handled by this arg parser.
        # Ignore its value
        i = i + 1
        continue

      try:
        # is this a boolean-valued argument?
        self.boolTrues.index(flag)
        # Yes it is. just set the property to 'true'
        self.targetProps.setProperty(prop, "True")
      except ValueError:
        # not a positive one at least. Check for nevative-logic
        try:
          self.boolFalses.index(flag)
          # it's a false flag
          self.targetProps.setProperty(prop, "False")
        except ValueError:
          # it's not this either. set the property to the next element of
          # the arg list
          i = i + 1
          arg = argList[i]
          self.targetProps.setProperty(prop, arg)

      # loop continuation
      i = i + 1

  def loadFromEnvironment(self):
    """ load properties from the user's environment into targetProperties """

    if self.targetProps == None:
      raise Exception("ArgParser not attached to Properties")

    for envVar in self.envVarMap.keys():
      val = os.getenv(envVar)
      if val != None:
        prop = self.envVarMap[envVar]
        self.targetProps.setProperty(prop, val)

  def usesFlag(self, arg):
    """ return the number of args consumed (1 for 'arg' itself, and 1
        for each parameter it takes) if we use a particular command
        line flag. Return 0 if we don't process it. """
    try:
      self.argVarMap[arg]

      # if it's a boolean switch, then it only consumes itself.
      try:
        self.boolTrues.index(arg)
        return 1
      except ValueError:
        pass

      try:
        self.boolFalses.index(arg)
        return 1
      except ValueError:
        pass

      # one for the flag and for its parameter
      return 2
    except KeyError:
      return 0

  def printUsage(self):
    keys = self.argVarMap.keys()
    keys.sort()

    # determine how much to indent properties
    maxKeyLen = 0
    for key in keys:
      keylen = len(key)
      if keylen > maxKeyLen:
        maxKeyLen = keylen
    maxKeyLen = maxKeyLen + 4 # maintain minimum padding

    for key in keys:
      pad = ""
      for i in range(0, maxKeyLen - len(key)):
        pad = pad + " "
      print key + pad  + self.argVarMap[key]
    print ""

