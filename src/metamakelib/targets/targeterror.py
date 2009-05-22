# (c) Copyright 2009 Cloudera, Inc.
#
# targeterror.py
# defines the TargetError object

class TargetError(Exception):
  """ Exception generated by Target objects """
  def __init__(self, target, value):
    self.target = target
    self.value = value

  def __str__(self):
    return "%s in %s" % (repr(self.value), self.target)
