# (c) Copyright 2009 Cloudera, Inc.
#
# pythontarget.py
# defines the following classes:
#  PythonBaseTarget (abstract)
#  PythonTarget
#  PythonTestTarget

import os

from   metamake.targets.targeterror import TargetError
from   metamake.targets.anttarget import AntTarget

class PythonBaseTarget(AntTarget):
  """ abstract class that has common code required by other python
      targets
  """

  def __init__(self):
    AntTarget.__init__(self)


  def language(self):
    return "python"


  def generates_preamble(self):
    return True

  def preamble(self):
    return self.emit_output_pathref()


  def antRule(self, rule):
    raise TargetError(self, "PythonBaseTarget is an abstract class")

  def copySource(self, src, dest):
    """ copy source code with the python copier to a destination dir """

    text = ""
    text = text + "  <exec executable=\"python\"\n"
    text = text + "    failonerror=\"true\">\n"
    text = text + "    <arg file=\"${python-copier}\" />\n"
    text = text + "    <arg value=\"" + src + "\" />\n"
    text = text + "    <arg value=\"" + dest + "\" />\n"
    text = text + "  </exec>\n"
    return text


  def buildAntRule(self, rule, outPath="${pythonoutdir}"):
    """ generate the compilation rule. This is the same as the code from
        PythonTarget() """

    outPath = self.normalize_user_path(outPath, is_dest_path=True)

    (mainName, ruleType) = self.splitRuleName(rule)

    text = "<target name=\"" + rule + "\" "
    depAntRules = self.getAntDependencies(ruleType, ["python-prereqs"])
    text = text + depAntRules
    text = text + ">\n"

    for src in self.getSources():
      text = text + self.copySource(self.normalize_user_path(src), outPath)

    for src in self.getDependencySourcesForLang("python"):
      text = text + self.copySource(src, outPath)

    text = text + self.copyDataPaths(outPath)
    text = text + "</target>\n"

    return text



class PythonTarget(PythonBaseTarget):
  """ Identifies a collection of python files which correspond to
      a script or library. Builds them into the common python source
      tree.

      Parameters:

      sources         Req - List of relative paths to source code.
                            Directories are recursively included.
      required_targets Opt - (Same as above)
      data_paths       Opt - paths containing data which need to
                            be present in the output dir
  """

  def __init__(self, sources, required_targets=None,
      data_paths=None):
    PythonBaseTarget.__init__(self)
    self.sources = sources
    self.required_targets = required_targets
    self.data_paths = data_paths

  def getSources(self):
    return self.sources

  def getOutputPaths(self):
    return [ "${pythonoutdir}/" ]

  def get_assembly_dir(self):
    return "${pythonoutdir}/"

  def get_ant_rule_map(self):
    # note: no cleanAntRules() because python-clean is a specially-generated
    # python target for this
    return {
      "build"        : self.getSafeName() + "-build",
      "python-build" : self.getSafeName() + "-build",
      "default"      : self.getSafeName() + "-build",
    }

  def antRule(self, rule):

    if rule == "preamble":
      return self.preamble()

    (mainName, ruleType) = self.splitRuleName(rule)

    if ruleType == "build":
      return self.buildAntRule(rule)
    else:
      raise TargetError(self, "Unknown rule type " + ruleType + " in " + self.getCanonicalName())


class PythonTestTarget(PythonBaseTarget):
  """ Identifies a collection of python files which correspond to
      a test fixture for a script or library
      Parameters:

      sources         Req - List of relative paths to source code.
                            Directories are recursively included.
      main_module      Req - The name of the python module containing
                            the top-level test suite to invoke
      required_targets Opt - (Same as above)
      data_paths       Opt - paths containing data which need to
                            be present in the output dir
  """

  def __init__(self, sources, main_module, required_targets=None,
      data_paths=None):
    PythonBaseTarget.__init__(self)
    self.sources = sources
    self.main_module = main_module
    self.required_targets = required_targets
    self.data_paths = data_paths

  def getSources(self):
    return self.sources


  def get_ant_rule_map(self):
    # note: no cleanAntRules() because python-clean is a specially-generated
    # python target for this
    return {
      "build"        : self.getSafeName() + "-build",
      "python-build" : self.getSafeName() + "-build",
      "test"         : self.getSafeName() + "-testshell",
      "test-inner"   : self.getSafeName() + "-test",
      "python-test"  : self.getSafeName() + "-test",
      "default"      : self.getSafeName() + "-test",
    }

  def getOutputPaths(self):
    return [ "${pythonoutdir}/" ]

  def getFullBuilddirectory(self):
    return "${pythonoutdir}/"


  def testShellAntRule(self, rule, mainName):
    """ Run the test rule and fail the build if the test fails """

    text = """
<target name="%(rule)s" depends="%(testrule)s">
  <fail if="failed" message="PyUnit test %(testname)s failed" />
</target>
""" % { "rule"     : rule,
        "testrule" : mainName + "-test",
        "testname" : self.getCanonicalName()
      }

    return text


  def testAntRule(self, rule):
    """ Actually run the test """

    (mainName, ruleType) = self.splitRuleName(rule)

    text = "<target name=\"" + rule + "\" depends=\"" + mainName \
        + "-build\">\n"
    text = text + "  <exec executable=\"python\""
    text = text + "    timeout=\"${python-test-timeout}\"\n"
    text = text + "    resultproperty=\"" + rule + "-result-prop\"\n"
    text = text + " dir=\"${pythonoutdir}\" failonerror=\"false\">\n"
    text = text + "    <arg value=\"-m\" />\n"
    text = text + "    <arg value=\"" + self.main_module + "\"/>\n"
    text = text + "  </exec>\n"
    text = text + "  <if name=\"" + rule + "-result-prop\" value=\"0\">\n"
    text = text + "    <else>\n"
    text = text + "      <property name=\"failed\" value=\"true\" />\n"
    text = text + "    </else>\n"
    text = text + "  </if>\n"
    text = text + "</target>\n"
    return text


  def antRule(self, rule):

    if rule == "preamble":
      return self.preamble()

    (mainName, ruleType) = self.splitRuleName(rule)

    if ruleType == "build":
      return self.buildAntRule(rule)
    elif ruleType == "test":
      return self.testAntRule(rule)
    elif ruleType == "testshell":
      return self.testShellAntRule(rule, mainName)
    else:
      raise TargetError(self, "Do not know how to make ruleType " + ruleType \
          + " in PythonTestTarget " + self.getCanonicalName())


