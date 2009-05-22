# (c) Copyright 2009 Cloudera, Inc.
#
# regproperty.py
# Defines RegisterProperty, which creates an Ant property bound to a particular value.

import os

from   metamake.targets.targeterror import TargetError
from   metamake.targets.target import *
from   metamake.targets.anttarget import *

class RegisterProperty(AntTarget):
  """ Creates a property in the build.xml file

      prop_name       Req - The property to create
      prop_val        Req - The value to assign to the property
  """

  def __init__(self, prop_name, prop_val):
    AntTarget.__init__(self)

    self.prop_name = prop_name
    self.prop_val = prop_val


  def generates_preamble(self):
    return True


  def antRule(self, rule):
    """ generates the XML to put in the buildfile
        for the ant rule (which will only ever be "preamble") """

    return """<property name="%(name)s" value="%(val)s" />\n""" % {
      "name" : self.substitute_macros(self.prop_name),
      "val"  : self.substitute_macros(self.prop_val)
    }

