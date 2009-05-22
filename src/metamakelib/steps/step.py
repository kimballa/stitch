# (c) Copyright 2009 Cloudera, Inc.
#
# module: step
# contains basic abstract Step class

from   metamakelib.targets.targeterror import TargetError

class Step(object):
  """ Base step object. A step is an item that goes into
      a package. Steps may be added to multiple packages.
  """

  def __init__(self):
    pass

  def register(self, package):
    """ Each Step "registers" with every package it is assigned to,
        to communicate any information back to the PackageTarget before
        operations are being constructed by any of them.

        This method might call some special-purpose callbacks in the
        PackageTarget object provided as an argument.

        This is done at constructor-time; no filenames or target objects
        are ready yet.
    """

    # Default behavior is to do nothing.
    pass


  def resolve(self, package):
    """ Each Step "resolves" the filenames of its dependencies and other
        input / output data, before any of them emit rule text. This is done
        after all construction is over, so all filenames, object references,
        etc are legal here.
    """

    # Default behavior is to do nothing.
    pass


  def getDependencies(self):
    return []

  def emitPackageOps(self, package):
    """ Main method to write the ant XML that puts this step into
        the named package.

        This is the abstract interface of this class.
    """
    raise TargetError(package, "Abstract Step.emitPackageOps() called")
