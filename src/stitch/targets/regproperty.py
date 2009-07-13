# (c) Copyright 2009 Cloudera, Inc.
#
# regproperty.py
# Defines RegisterProperty, which creates an Ant property bound to a particular value.

import os

from   stitch.targets.targeterror import TargetError
from   stitch.targets.target import *
from   stitch.targets.anttarget import *

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
      "name" : self.substitute_macros(self.force(self.prop_name)),
      "val"  : self.substitute_macros(self.force(self.prop_val))
    }


class BacktickProperty(AntTarget):
  """
  Creates a property in the build.xml file which is set by running
  an external command

    prop_name       Req    - The property to create
    executable      Req    - The command to run
    arguments       Opt    - A list of arguments to pass
    dir             Opt    - The working directory
    env             Opt    - A dictionary of environment variables
    fail_on_error   Opt    - Stop execution on non-zero exit code
  """

  def __init__(self, prop_name, executable, arguments=None, dir=None,
               env=None, fail_on_error=True):
    AntTarget.__init__(self)

    self.prop_name = prop_name
    self.executable = executable
    self.arguments = arguments if arguments else []
    self.dir = dir
    self.env = env if env else {}
    self.fail_on_error = fail_on_error

  def generates_preamble(self):
    return True


  def antRule(self, rule):
    """ generates the XML to put in the buildfile
        for the ant rule (which will only ever be "preamble") """

    options = {
      'executable': self.executable,
      'outputproperty': self.prop_name
      }
    if self.dir:
      options['dir'] = self.dir

    if self.fail_on_error:
      options['failonerror'] = 'true'

    def process_val(val):
      return self.substitute_macros(
        self.normalize_select_user_path(self.force(val)))
    options_str = " ".join(
      ["%s=\"%s\"" % (key, process_val(val))
       for key, val in options.iteritems()])

    ret = "<exec %s>\n" % options_str
    for arg in self.arguments:
      ret += """  <arg value="%s" />\n""" % \
             self.substitute_macros(self.force(arg))
    for env_key, env_val in self.env.iteritems():
      ret += """  <env key="%s" value="%s" />\n""" % (
        self.normalize_user_path(self.force(env_key)),
        self.normalize_user_path(self.force(env_val)))

    ret += """</exec>\n"""
    return ret
