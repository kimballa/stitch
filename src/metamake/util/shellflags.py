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
# flags specific to shell operation.
# can inherit values from other flag objects
#
################################################
# This module is deprecated
# New code should not depend on this module
################################################
#
# This is only used by the (deprecated) c.c.tools.oldshell.py module

import os


class ShellFlags(object):
  """ flags specific to running shell cmds """

  def __init__(self):
    self.printShellCmd = False
    self.printScpCmd = False
    self.username = os.getenv("USER")
    self.sshopts = "-o StrictHostKeyChecking=no"


  def loadFlags(self, otherFlags):
    """ loads flags from another object """

    self.printShellCmd = getattr(otherFlags, "printShellCmd", \
        self.printShellCmd)
    self.printScpCmd = getattr(otherFlags, "printScpCmd", self.printScpCmd)
    self.username = getattr(otherFlags, "username", self.username)
    self.sshopts = getattr(otherFlags, "sshopts", self.sshopts)

    return self


