# (c) Copyright 2009 Cloudera, Inc.
#
# exec.py
# Defines the Exec type which allows you to execute any arbitrary
# command; this is effectively a wrapper around ant's <exec>.
#

import os

import stitch.steps.step as step

class Exec(step.Step):
  """
    Defines the Exec type which allows you to execute any arbitrary
    command; this is effectively a wrapper around ant's <exec>.

    Commands run, by default, in the package assembly directory.

    Arguments:

    executable          Req  What command to run
    arguments           Opt  A list of arguments to pass to the command.
    dir                 Opt  Working directory where the command will be run.
    fail_on_error       Opt  boolean; default is True. If this command exits
                             with non-zero status, the build fails if this is
                             true.
    force_build         Opt  boolean; default is False. If True, then this
                             step cannot be satisfied by an uptodate
                             check.
    inputs              Opt  A list of files or dirs which are inputs to this
                             command. If they're newer than the last time it
                             was executed, this will rebuild the target.
                             Dirs must end with '/'.

    Performs macro expansion per Target.substitute_macros() on all inputs.
  """

  def __init__(self, executable, arguments=None, dir=None, fail_on_error=True,
      force_build=False, inputs=None):
    step.Step.__init__(self)

    self.executable = executable
    self.arguments = arguments
    self.working_dir = dir
    self.fail_on_error = fail_on_error
    self.force_build = force_build

    if inputs != None:
      self.inputs = inputs
    else:
      self.inputs = []


  def resolve(self, package):
    if self.force_build:
      package.resolved_forced_build()
    else:
      for input in self.inputs:
        input = self.__substitute(input, package)
        if input.endswith(os.sep):
          package.resolved_input_dir(input)
        else:
          package.resolved_input_file(input)


  def __substitute(self, value, package):
    """ Substitute values in for macros in user strings """

    value = package.normalize_select_user_path(value)
    return package.substitute_macros(value)


  def emitPackageOps(self, package):

    text = ""

    real_exec = self.__substitute(self.executable, package)
    text = text + "  <exec executable=\"" + real_exec + "\"\n"
    if self.fail_on_error:
      text = text + "    failonerror=\"true\"\n"
    if self.working_dir == None:
      # Run the command wherever we're doing the assembly.
      text = text + "    dir=\"" + package.get_assembly_dir() + "\">\n"
    else:
      real_working_dir = package.normalize_user_path(self.working_dir, is_dest_path=True)
      text = text + "    dir=\"" + real_working_dir + "\">\n"

    if self.arguments != None:
      for arg in self.arguments:
        arg = self.__substitute(arg, package)
        text = text + "     <arg value=\"" + arg + "\" />\n"

    text = text + "  </exec>\n"
    return text


