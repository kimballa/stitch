# (c) Copyright 2009 Cloudera, Inc.
#
# testset.py
# Defines TestSetTarget, which executes a set of test cases, and the
# TestCase class which defines a test case within a test set.

import os

from   stitch.targets.targeterror import TargetError
from   stitch.targets.target import *
from   stitch.targets.anttarget import *


class TestSetTarget(AntTarget):
  """ Executes a set of TestCase's and returns success/fail based on the
      outcome of these program executions.

      An entire test set will run, even if individual TestCase elements
      are recorded as failures.

      phase: test

      test_target      Req - The build target that defines the
                            program under test.
      testcases       Req - The list of TestCase objects to execute
      test_set_name     Opt - A user-friendly name for this test suite
      required_targets Opt - Any additional targets which must be built first
  """

  def __init__(self, test_target, testcases, test_set_name=None,
      required_targets=None):

    AntTarget.__init__(self)
    self.test_target = test_target
    self.testcases = testcases
    self.test_set_name = test_set_name

    if required_targets == None:
      required_targets = []
    required_targets.append(self.test_target)

    self.required_targets = required_targets

    # counter used for unique test case id generating
    self.test_case_id = 0


  def getNewTestCaseId(self):
    """ Return a test case id string for a test case within the test set."""
    this_id = self.test_case_id
    self.test_case_id = self.test_case_id + 1

    return self.getSafeName() + "-testcase-" + str(this_id)


  def getFailureProp(self):
    """ What property should TestCases set on failure? """
    return self.getSafeName() + "-test-failed"


  def getTestSetName(self):
    """ Return the user-friendly name for this test set """

    if self.test_set_name != None:
      return self.test_set_name
    else:
      return self.getCanonicalName()


  def getExecPath(self):
    """ What path should be used as the working dir for executing the test? """

    target_obj = self.getTargetByName(self.test_target)
    if target_obj == None:
      raise TargetError(self, "No such target: " + self.test_target)

    return target_obj.get_assembly_dir()


  def get_ant_rule_map(self):
    return {
      "test-inner" : self.getSafeName() + "-test",
      "test" : self.getSafeName() + "-testshell",
      "default" : self.getSafeName() + "-testshell"
    }


  def antRule(self, rule):
    """ generates the XML to put in the buildfile
        for the ant rule """

    (mainName, ruleType) = self.splitRuleName(rule)

    if ruleType == "test":
      return self.testRule(rule, mainName)
    elif ruleType == "testshell":
      return self.testShellRule(rule, mainName)


  def testShellRule(self, rule, mainName):
    """ Run the test rule and fail the build if the test fails """

    text = """
<target name="%(rule)s" depends="%(testrule)s">
  <fail if="failed" message="Unit test set failed: %(testname)s" />
</target>
""" % { "rule"     : rule,
        "testrule" : mainName + "-test",
        "testname" : self.getTestSetName()
      }

    return text


  def testRule(self, rule, mainName):

    text = "<target name=\"" + rule + "\" "
    depAntRules = self.getAntDependencies("build")
    text = text + depAntRules + ">\n"

    set_name_str = self.getTestSetName()

    text = text + "  <echo message=\"Running test set: " + set_name_str \
        + "\"/>\n"

    # Generate code for each test case in the set
    for testcase in self.testcases:
      text = text + testcase.emitTestCaseText(self)

    # If any of these test cases failed, then set the global fail flag
    # and print a message
    text = text + """
  <if name="%(failprop)s">
    <echo message="Test set failed: %(setname)s" />
    <property name="failed" value="true" />
  </if>
</target>
""" % { "failprop" : self.getFailureProp(),
        "setname"  : set_name_str }

    return text


class TestCase(object):
  """ TestCase defines a single test case within a test set. The test case
      presents a program to run, optionally with a set of arguments, and
      an expected result. This can be expectSuccess--a return code of 0--or
      expectError--a non-zero return code--or any specific status code
      with expectStatus.

      The test case is executed in the output directory of the target
      under test indicated in the TestSetTarget

      executable      Req - The program to run
      args            Opt - Any arguments to supply
      name            Opt - A user-friendly name for this test case
      timeout         Opt - A timeout to use; default is 10 seconds. Set to 0
                            for an infinite timeout.
      expectStatus    Opt - The exact status code to expect on return
      expectSuccess   Opt - Boolean; if True, expect 0 return status
      expectError     Opt - Boolean; if True, expect non-zero return status
  """

  def __init__(self, executable, args=None, name=None, timeout=None, \
      expectStatus=0, expectSuccess=None, expectError=None):
    self.executable = executable
    self.args = args
    self.timeout = timeout
    self.name = name

    # if one of expectSuccess or expectError is true, then this takes precedence
    # otherwise, we use the expectStatus code.
    if expectSuccess == True and expectError == True:
      raise Exception("Ambiguous outcome predicted for test case")

    self.expectStatus = expectStatus
    self.expectSuccess = expectSuccess
    self.expectError = expectError


  def emitTestCaseText(self, test_set):
    """ Generate the ant xml to run the test case """

    text = ""

    # what property to set to capture this test case's result?
    result_prop_name = test_set.getNewTestCaseId()

    if self.name == None:
      # Just use the gensym'd test case id for the test case naem
      case_name = fail_prop_name
    else:
      text = text + "  <echo message=\"Running test case: " + self.name \
          + "\" />\n"
      case_name = self.name

    # what property signals failure of the overall test set?
    test_set_fail_prop = test_set.getFailureProp()

    exec_dir = test_set.getExecPath()

    if self.timeout == 0:
      # No timeout
      timeout_str = ""
    elif self.timeout == None:
      # Default timeout
      timeout_str = "timeout=\"${default-test-case-timeout}\""
    else:
      # User-specified timeout:
      timeout_str = "timeout=\"" + self.timeout + "\""

    if self.args == None:
      arg_str = ""
    else:
      arg_str = "<arg line=\"" + str(self.args) + "\" />"

    # TODO(aaron): if this returns a non-zero exit code, it prints
    # that fact to the screen. Can we disable this, knowing that we
    # validate the actual return code vs an expected one anyway?

    # Despite ant's claim that it exits with status '-1' on timeout
    # this seems to be rendered as status 143.
    text = text + """
  <exec executable="%(program)s" dir="%(execdir)s"
    resultproperty="%(resultprop)s" %(timeout)s
    resolveexecutable="true">
    %(args)s
  </exec>
  <if name="%(resultprop)s" value="143">
    <property name="%(setfailprop)s" value="true" />
    <echo message="Test case failed: %(casename)s (Timeout)"/>
  </if>
""" % {
      "program"     : self.executable,
      "execdir"     : exec_dir,
      "resultprop"  : result_prop_name,
      "timeout"     : timeout_str,
      "args"        : arg_str,
      "setfailprop" : test_set_fail_prop,
      "casename"    : case_name
    }

    if self.expectSuccess:
      # Set the failure case on non-zero return
      text = text + """
  <if name="%(resultprop)s" value="0">
    <else>
      <property name="%(setfailprop)s" value="true" />
      <echo message="Test case failed: %(casename)s (Expected exit 0)"/>
    </else>
  </if>
""" % {
      "resultprop"  : result_prop_name,
      "setfailprop" : test_set_fail_prop,
      "casename"    : case_name
    }
    elif self.expectError:
      # Set the failure case on zero return
      text = text + """
  <if name="%(resultprop)s" value="0">
    <property name="%(setfailprop)s" value="true" />
    <echo message="Test case failed: %(casename)s (Expected error exit)"/>
  </if>
""" % {
      "resultprop"  : result_prop_name,
      "setfailprop" : test_set_fail_prop,
      "casename"    : case_name
    }
    else:
      # Set the failure case on exit status mismatch
      text = text + """
  <if name="%(resultprop)s" value="%(status)s">
    <else>
      <property name="%(setfailprop)s" value="true" />
      <echo message="Test case failed: %(casename)s (Expected status %(status)s;
 got ${%(resultprop)s})"/>
    </else>
  </if>
""" % {
      "resultprop"  : result_prop_name,
      "status"      : str(self.expectStatus),
      "setfailprop" : test_set_fail_prop,
      "casename"    : case_name
    }

    return text

