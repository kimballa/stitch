# (c) Copyright 2009 Cloudera, Inc.
#
# module: raw
# Defines the RawAntXml Step

import metamakelib.steps.step as step

class RawAntXml(step.Step):
  """ Performs the ant task(s) given as raw XML by the user. This is a
      "hole" in the metamake packaging system to allow you to work around
      corners if the simple assembly steps we directly provide for are not
      sufficient. Hopefully, you will use this sparingly. If there's a
      step-like action that is common to more than one target, we
      should really just build it into metamake as its own Step class. """

  def __init__(self, step_xml):
    step.Step.__init__(self)
    self.step_xml = step_xml


  def emitPackageOps(self, package):
    return package.expand_macros(self.step_xml)


