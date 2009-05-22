# (c) Copyright 2009 Cloudera, Inc.
#
# vertarget.py
# Defines VerStringTarget, which creates an intermediate src file containing
# version string information.

import os

from   metamake.targets.targeterror import TargetError
from   metamake.targets.target import *
from   metamake.targets.anttarget import *

class VerStringTarget(AntTarget):
  """ Creates a module/class containing version string information for a
      project.

      Can create modules for python and/or Java.

      phase: build

      version        Req - The version string to use
      python_module   Opt - The name of the python module to generate
      java_class      Opt - The name of the Java class to generate

      By default, the string '-test' will be appended to the version
      string supplied. This can be overridden by setting the ant
      property 'release' to true, e.g.:

        build -Drelease=true targetname...
  """

  def __init__(self, version, python_module=None, java_class=None):
    AntTarget.__init__(self)

    self.version = version
    self.python_module = python_module
    self.java_class = java_class
    self.required_targets = None


  def language(self):
    return "python" # TODO(aaron) This should be able to return a list.


  def get_ant_rule_map(self):
    return {
      "build"   : self.getSafeName() + "-build",
      "default" : self.getSafeName() + "-build",
      "clean"   : self.getSafeName() + "-clean"
    }


  def get_version(self):
    """ Return the version string that should be used by depending targets """
    return self.version + "${test-suffix}"

  def simple_build_rule(self, rule_name):
    """ If there is nothing to generate, make a null rule. """
    text = "<target name=\"" + rule_name + "\" "
    depAntRules = self.getAntDependencies("build", [ "release-version" ])
    text = text + depAntRules + "/>\n"
    return text


  def antRule(self, rule):
    """ generates the XML to put in the buildfile
        for the ant rule """

    (mainName, ruleType) = self.splitRuleName(rule)

    if ruleType == "clean":
      return self.cleanRule(rule)

    if self.python_module == None and self.java_class == None:
      return self.simple_build_rule(rule)

    text = "<target name=\"" + rule + "\" "
    depAntRules = self.getAntDependencies(ruleType, [ "release-version" ])
    text = text + depAntRules + ">\n"

    intermediate_dir = self.getIntermediatePath()
    status_file = os.path.join(intermediate_dir, "status.file")

    # TODO(aaron): Currently, we generate the uptodate property for
    # this rule but don't actually test it in an <if exists... > block.
    # This is because if you recompile with -Drelease=true, then we
    # want to force regeneration. Similarly, if you then subsequently
    # compile a third time without -Drelease, then we want to revert.
    # The simplest solution is to just always recompile. This technically
    # screws up dependencies and causes extraneous "recompilation." For
    # Java programs, this is a time suck. For python programs, it's just
    # a single extra file copy every time. If we do uswe with java a lot,
    # we will need to figure out how to be more clever.

    # lazy import to defeat circular reference.
    import metamake.buildfile as buildfile

    text = text + """
  <mkdir dir="%(intermediate_dir)s" />
  <delete file="%(status_file)s" />
  <dependset>
    <srcfileset dir="${basedir}">
      <include name="%(targetsfile)s" />
      <include name="*/%(targetsfile)s" />
      <include name="**/%(targetsfile)s" />
      <exclude name="bin/*" />
      <exclude name="bin/**" />
    </srcfileset>
    <targetfileset dir="%(intermediate_dir)s" includes="**/*" />
  </dependset>
  <copy todir="%(intermediate_dir)s">
    <fileset dir="%(intermediate_dir)s">
      <include name="**/*.java" />
      <include name="**/*.py" />
    </fileset>
    <mapper type="merge" to="status.file" />
  </copy>
  <available property="%(rule)s-uptodate" file="%(status_file)s" />

""" % { "intermediate_dir" : intermediate_dir,
        "status_file"      : status_file,
        "rule"             : rule,
        "targetsfile"      : buildfile.DEFAULT_BUILD_FILENAME
      }

    if self.python_module != None:
      text = text + """
    <exec executable="${make-version-exec}" dir="${basedir}">
      <arg value="--lang" />
      <arg value="python" />
      <arg value="--modname" />
      <arg value="%(pymodule)s" />
      <arg value="--basepath" />
      <arg value="%(intermediate_dir)s/gen-py" />
      <arg value="--verstring" />
      <arg value="%(verstring)s${test-suffix}" />
    </exec>
""" % { "pymodule"         : self.python_module,
        "intermediate_dir" : intermediate_dir,
        "verstring"        : self.version
      }

    if self.java_class != None:
      text = text + """
    <exec executable="${make-version-exec}" dir="${basedir}">
      <arg value="--lang" />
      <arg value="java" />
      <arg value="--modname" />
      <arg value="%(javaclass)s" />
      <arg value="--basepath" />
      <arg value="%(intermediate_dir)s/gen-java" />
      <arg value="--verstring" />
      <arg value="%(verstring)s${test-suffix}" />
    </exec>
""" % { "javaclass"        : self.java_class,
        "intermediate_dir" : intermediate_dir,
        "verstring"        : self.version
      }

    text = text + "</target>\n"
    return text


  def getIntermediatePath(self):
    """ return the path where the thrift output goes """
    return os.path.join("${genfiles-outdir}/" + self.getBuildDirectory(),
        "${version-subdir}")

  def get_assembly_dir(self):
    return self.getIntermediatePath()

  def get_python_path(self):
    """ Return the path generated for python. This contains the
        initial module component, due to a quirk in copyPy.py requiring
        that.
    """

    if self.python_module == None:
      return ""

    python_mod_parts = self.python_module.split(".")
    initial_module = python_mod_parts[0]
    if len(python_mod_parts) == 1:
      initial_module = initial_module + ".py"

    return self.getIntermediatePath() + "/gen-py/" \
      + initial_module


  def intermediatePathsForLang(self, lang):
    """ return paths specific to a given language """

    if lang == "python" and self.python_module != None:
      return [ self.get_python_path() ]
    elif lang == "java" and self.java_class != None:
      return [ self.getIntermediatePath() + "/gen-java/" ]
    else:
      return []


  def intermediatePaths(self):
    """ return paths to external clients """

    outList = []
    if self.python_module != None:
      outList.append(self.get_python_path())
    if self.java_class != None:
      outList.append(self.getIntermediatePath() + "/gen-java")

    return outList


  def cleanRule(self, rule):
    """ a rule to clean the genfiles output """
    text = "<target name=\"" + rule + "\">\n"
    dest_dir = self.getIntermediatePath()
    text = text + "  <delete dir=\"" + dest_dir + "\" />\n"
    text = text + "</target>\n"
    return text


