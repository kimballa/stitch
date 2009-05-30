#
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
# Extends Java properties file behavior with semantics used by Ant.
# Properties is from stitch.util.properties; this implements
# java.util.Properties.
#
# We extend this with the following contracts, based on how ant loads
# and uses properties:
#
# properties can be set only once and are then read-only
# properties can contain one level of nested  "${propname}" elements
# which are auto-resolved
#


from stitch.util.properties import Properties


# don't allow infinitely deep resolution of nested properties; this really
# probably signifies an infinite loop somewhere.
# Technically, we should construct a DAG of properties and look for cycles,
# but this is a lot easier and probably just as well.
MAX_RESOLVE_DEPTH = 50

class AntProperties(Properties):
  """ Reads and resolves Java properties files with Apache Ant
      loading semantics. """

  def setProperty(self, key, value):
    """ only set key if it's not already set """

    cur = self.getProperty(key, None)
    if cur == None:
      Properties.setProperty(self, key, value)

  def getProperty(self, key, defaultVal=None, depth=0):
    """ Return the value of a property; resolve ${propname} elements
        nested in the string """

    val = Properties.getProperty(self, key, None)
    if val == None:
      # just return default val (unparsed)
      return defaultVal
    else:
      return self.resolveProperties(val, depth)


  def resolveProperties(self, val, depth=0):
    """ given a string containing "${property}" substrs, resolve
        these and return the result string. """
    global MAX_RESOLVE_DEPTH

    if depth > MAX_RESOLVE_DEPTH:
      raise ValueError("Max resolution depth reached in property")

    while val.find("${") != -1:
      # resolve nested entry
      start = val.find("${")
      end = val.find("}", start)
      if -1 == end:
        raise ValueError("Key " + key + " returns invalid-formed value")
      subkey = val[start + 2:end]
      subval = self.getProperty(subkey, "", depth + 1)
      val = val[0:start] + subval + val[end + 1:]

    return val

