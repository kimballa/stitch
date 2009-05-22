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
# A class that subclasses TestCase with more assert functions

import unittest

class TestCaseWithAsserts(unittest.TestCase):

  def __init__(self, methodName='runTest'):
    unittest.TestCase.__init__(self, methodName)

  def assertNone(self, first, msg=None):
    self.assertEqual(first, None, msg)

  def assertNotNone(self, first, msg=None):
    self.assertNotEqual(first, None, msg)

  def assertTrue(self, first, msg=None):
    self.assertEqual(first, True, msg)

  def assertFalse(self, first, msg=None):
    self.assertEqual(first, False, msg)

  def fail(self, msg="fail()"):
    self.assertTrue(False, msg)
