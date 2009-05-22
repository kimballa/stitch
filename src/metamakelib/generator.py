# (c) Copyright 2009 Cloudera, Inc.
#
# Classes which take a graph of BuildFiles and
# Targets and generate some output plans; e.g.,
# ant-directed builds, Eclipse workspace generator, etc.


class GeneratorError(Exception):
  """ Error/exception caused when running a generator """

  def __init__(self, value):
    self.value = value

  def __str__(self):
    return repr(self.value)


class Generator(object):
  """ Base class for all Generators """

  def __init__(self):
    pass

  def generate(self, allTargets):
    raise GeneratorError("Generator.generate() is abstract")

  def isPublic(self):
    """ return True if users should be able to instantiate
        this generator directly. """
    return False

  def getDescription(self):
    """ Return a string describing the generator. Required
        if isPublic() returns true. """
    raise GeneratorError("Generator class is abstract")

  def getEnableFlag(self):
    """ return a line for the script which sets flags to
        enable steps from this generator in top-level
        built-in targets """
    return ""

  def getTopLevelScript(self, allTargets):
    """ return the text which should be included in the top-level
        script, as generated by this sub-generator. """
    return ""



