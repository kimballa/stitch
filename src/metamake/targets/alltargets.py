# (c) Copyright 2009 Cloudera, Inc.
#
# alltargets.py
# defines the Target object and all of its
# subclasses. The user "Targets" files actually
# call c'tors for a bunch of objects repeatedly.
#
# The objects then add themselves to the current
# build file
#
# This is the only module imported by c.c.build.buildfile into the space
# where the targets get compiled -- so this must include and reexport all
# other public Target subclass modules

import os

# I realize that this import block looks very divergent from the style guide.
# This is actually less about python, and more about a fundamental way that
# metamake works.
#
# The Targets file is executed in an environment that is a copy of alltargets'
# environment. So all the PackageTarget(), JarTarget(), etc, constructors, are
# all the public elements of this module. This module is gradually being refactored;
# eventually alltargets.py will be only a pure import module and all existing Target
# subclasses will migrate into separate modules.

import metamake.antgenerator as antgenerator
import metamake.paths as paths

from   metamake.steps.antcall import *
from   metamake.steps.enablecontrib import *
from   metamake.steps.execstep import *
from   metamake.steps.filesteps import *
from   metamake.steps.hadoopcomponent import *
from   metamake.steps.outputsteps import *
from   metamake.steps.raw import *
from   metamake.steps.rpmbuild import *
from   metamake.steps.step import *
from   metamake.steps.tar import *

from   metamake.targets.targeterror import TargetError
from   metamake.targets.target import *
from   metamake.targets.anttarget import *
from   metamake.targets.javatargets import *
from   metamake.targets.packagetarget import *
from   metamake.targets.pythontarget import *
from   metamake.targets.pythonredisttarget import *
from   metamake.targets.regproperty import *
from   metamake.targets.rsynctarget import *
from   metamake.targets.stepwise import *
from   metamake.targets.testset import *
from   metamake.targets.vertarget import *

class RawAntTarget(AntTarget):
  """ Injects raw user-specified XML into the build.xml file.
      Parameters:

      buildXml          Opt - XML to include in Ant file for the 'build'
                              rule
      buildRuleName     Opt - If None (and buildXml is not None) metamake
                              will generate the <target> .. </target>
                              wrapper around the buildXml, using a
                              metamake-generated name. If this is set,
                              then buildXml is assumed to be a full
                              specification including the <target> wrapper.
      cleanXml          Opt - XML to include in Ant file for the 'clean' rule
      cleanRuleName     Opt - Functions like buildRuleName
      testXml           Opt - like cleanXml
      testRuleName      Opt - like cleanRuleName
      required_targets   Opt - List of other projects/dirs containing
                              Targets files required by this project.
      classpath_elements Opt - A list of paths that should be added
                              to the classpath when compiling/running
                              the outputs
      sources           Opt - List of relative paths to source code. May be
                              directories (included recursively)
      outputs           Opt - List of output dirs/jars created by this rule.
      standalone_exempt  Opt - See JarTarget

      Note that specifying rule names means that you must manually
      manage your own depends="..." clause for your target.

      In general, this target is intended to be used lightly. If you
      absolutely must define a custom target in the build file, you
      may use this. If you're defining a means to use a particular
      tool, though, it's probably better to create a real Target in
      metamake so that it can be reused and integrate with the rest of
      the dependency tracking system.
  """

  def __init__(self, buildXml=None, buildRuleName=None, cleanXml=None,
      cleanRuleName=None, testXml=None, testRuleName=None,
      required_targets=None, classpath_elements=None,
      sources=None, outputs=None, standalone_exempt=False):
    AntTarget.__init__(self)
    self.buildXml = buildXml
    self.buildRuleName = buildRuleName
    self.cleanXml = cleanXml
    self.cleanRuleName = cleanRuleName
    self.testXml = testXml
    self.testRuleName = testRuleName
    self.required_targets = required_targets
    self.classpath_elements = classpath_elements
    self.sources = sources
    self.outputs = outputs
    self.standalone_exempt = standalone_exempt

  def generates_preamble(self):
    return True

  def isStandaloneExempt(self):
    return self.standalone_exempt

  def get_ant_rule_map(self):
    map = {}

    if self.buildXml != None:
      if self.buildRuleName != None:
        map["build"] = self.buildRuleName
        map["default"] = self.buildRuleName
      else:
        map["build"] = self.getSafeName() + "-build"
        map["default"] = self.getSafeName() + "-build"

    if self.cleanXml != None:
      if self.cleanRuleName != None:
        map["clean"] = self.cleanRuleName
      else:
        map["clean"] = self.getSafeName() + "-clean"

    if self.testXml != None:
      if self.testRuleName != None:
        map["test"] = self.testRuleName
        map["default"] = self.testRuleName
      else:
        map["test"] = self.getSafeName() + "-test"
        map["default"] = self.getSafeName() + "-test"

    return map

  def antRule(self, rule):
    """ generates ant rules """

    # first, check to see if we can just dispatch it as a "raw" rule.
    if rule == "preamble":
      return self.output_target_preamble()
    elif rule == self.buildRuleName:
      return self.buildXml
    elif rule == self.cleanRuleName:
      return self.cleanXml
    elif rule == self.testRuleName:
      return self.testXml

    # if we're here, then we have to generate the <target> .. </target>
    # that goes around some rule.
    (mainName, ruleType) = self.splitRuleName(rule)

    text = "<target name=\"" + rule + "\" "

    if ruleType == "clean":
      text = text + ">\n"
      text = text + self.cleanXml
    elif ruleType == "test":
      if self.buildXml != None:
        text = text + "depends=\"" + self.buildAntRules()[0] + "\">\n"
      else:
        text = text + ">\n"
      text = text + self.testXml
    elif ruleType == "build":
      depAntRules = self.getAntDependencies(ruleType)
      text = text + depAntRules + ">\n"
      text = text + self.buildXml

    text = text + "</target>\n"
    return text




class MakefileTarget(AntTarget):
  """ Identifies a Makefile-driven build.
      Parameters:

      makefileName    Opt - Name of the Makefile (default: "Makefile")
      required_targets Opt - (Same as above)
      defaultRule     Opt - Rule name to execute on the target
      cleanRule       Opt - name of rule to run for cleaning ("clean")
      testRule        Opt - name of rule to run for testing
      outputs         Opt - A list of output objects created by this rule
      makeOptions     Opt - Arguments to pass to make on command line
      debugOptions    Opt - Arguments to pass to make for debug mode cmdline
  """

  def __init__(self, makefileName="Makefile", required_targets=None,
      defaultRule=None, cleanRule="clean", testRule=None,
      outputs=None, makeOptions=None, debugOptions=None):

    AntTarget.__init__(self)
    self.makefileName = makefileName
    self.required_targets = required_targets
    self.defaultRule = defaultRule
    self.cleanRule = cleanRule
    self.testRule = testRule
    self.outputs = outputs
    self.makeOptions = makeOptions
    self.debugOptions = debugOptions


  def generates_preamble(self):
    return True

  def get_ant_rule_map(self):
    map = {
      "build" : self.getSafeName() + "-build",
      "clean" : self.getSafeName() + "-clean"
    }

    if self.testRule != None:
      map["test"] = self.getSafeName() + "-test"
      map["default"] = self.getSafeName() + "-test"
    else:
      map["default"] = self.getSafeName() + "-build"

    return map


  def antRule(self, rule):

    if rule == "preamble":
      return self.emit_output_pathref()

    (mainName, ruleType) = self.splitRuleName(rule)

    if ruleType == "clean":
      makefileTarget = self.cleanRule
    elif ruleType == "build":
      makefileTarget = self.defaultRule
    elif ruleType == "test":
      makefileTarget = self.testRule
    else:
      raise TargetError(self, "Error: Makefile cannot generate rule type \"" \
          + ruleType + "\"")

    text = "<target name=\"" + rule + "\" "
    if ruleType == "build":
      depAntRules = self.getAntDependencies(ruleType)
      text = text + depAntRules
    elif ruleType == "test":
      text = text + "depends=\"" + mainName + "-build\" "
    text = text + ">\n"

    makeDirectory = self.getBuildFile().getBuildFileDirectory()

    if self.debugOptions != None:
      text = text + "  <if name=\"debug\">"
      text = text + self.execCore(makefileTarget, makeDirectory,
          "<arg line=\"" + self.debugOptions + "\" />\n")
      text = text + "    <else>\n"
      text = text + self.execCore(makefileTarget, makeDirectory, "")
      text = text + "    </else>\n"
      text = text + "  </if>"
    else:
      text = text + self.execCore(makefileTarget, makeDirectory, "")

    text = text + "</target>\n"

    return text


  def execCore(self, makefileTarget, makeDirectory, additionalArgs):
    """ return the central <exec> fn to run in the target. """

    text = "    <exec executable=\"${make-exec}\"\n"
    text = text + "      failonerror=\"true\">\n"
    text = text + "      <arg value=\"-C\" />\n"
    text = text + "      <arg file=\"${basedir}" + os.sep \
        + makeDirectory + "\" />\n"

    if self.makefileName != None:
      text = text + "      <arg value=\"-f\" />\n"
      text = text + "      <arg value=\"" + self.makefileName + "\" />\n"

    if self.makeOptions != None:
      text = text + "      <arg line=\"" + self.makeOptions + "\" />\n"

    text = text + additionalArgs

    text = text + "      <arg value=\"" + makefileTarget + "\" />\n"
    text = text + "    </exec>\n"

    return text


  def outputPaths(self):
    return self.outputs


class ThirdPartyAntTarget(AntTarget):
  """ Identifies a third-party source target which
      includes its own build.xml intended to be used as a
      standalone Ant project.

      Parameters:
      buildfile_name   Opt - Name of the build file (default: "build.xml")
      required_targets Opt - List of projects/dirs containing Targets files
                            (as above)
      ant_target       Opt - Name of ant target to call by default
      clean_target     Opt - Name of ant target to call to clean
      test_target      Opt - Name of ant target to call to run unit tests
      sources         Opt - List of source directories used by this rule
      outputs         Opt - List of output objects (either .jar files
                            or dirs of .class files) created by this rule
      classpath_elements  Opt - List of elements to put on classpath when
                               running the output of what this creates
      properties      Opt - Dictionary of properties to set in subant call
  """
  # TODO: Support debug mode builds of subants

  def __init__(self, buildfile_name="build.xml", required_targets=None,
      ant_target=None, clean_target="clean", test_target="test",
      sources=None, outputs=None, classpath_elements=None, properties=None):

    AntTarget.__init__(self)
    self.buildfile_name = buildfile_name
    self.required_targets = required_targets
    self.ant_target = ant_target
    self.clean_target = clean_target
    self.test_target = test_target
    self.sources = sources
    self.outputs = outputs
    self.classpath_elements = classpath_elements
    self.properties = properties


  def generates_preamble(self):
    return True

  def get_ant_rule_map(self):
    return {
      "build" : self.getSafeName() + "-build",
      "clean" : self.getSafeName() + "-clean",
      "default" : self.getSafeName() + "-build"
    }


  def language(self):
    return "java"

  def antRule(self, rule):
    """ generates the XML to put in the buildfile
        for the ant rule; invokes another copy of
        ant via <exec> to do the work required. """

    if rule == "preamble":
      return self.output_target_preamble()

    (mainName, ruleType) = self.splitRuleName(rule)

    text = "<target name=\"" + rule + "\" "
    depAntRules = self.getAntDependencies(ruleType)
    text = text + depAntRules + ">\n"

    if ruleType == "build" and self.ant_target != None:
      outTargetStr = self.ant_target
    elif ruleType == "clean":
      outTargetStr = self.clean_target
    elif ruleType == "test":
      outTargetStr = self.test_target
    else:
      outTargetStr = None

    # get the directory that held our Targets file.
    # this is where we invoke ant
    build_file = self.getBuildFile()
    dirName = build_file.getBuildFileDirectory()

    text = text + "  <exec executable=\"${ant-exec}\"\n"
    text = text + "    failonerror=\"true\"\n"
    text = text + "    dir=\"" + dirName + "\">\n"
    text = text + "    <arg value=\"-f\" />\n"
    text = text + "    <arg value=\"" + self.buildfile_name + "\" />\n"
    if self.properties != None:
      for propname in self.properties:
        propval = self.properties[propname]
        propArg = "-D" + propname + "=" + propval
        text = text + "     <arg value=\"" + propArg + "\" />\n"
    if outTargetStr:
      text = text + "    <arg value=\"" + outTargetStr + "\" />\n"
    text = text + "  </exec>\n"
    text = text + "</target>\n"
    return text


  def outputPaths(self):
    """ return whatever the user claimed the outputs are """
    if self.outputs == None:
      return []
    else:
      return self.outputs



class EmptyTarget(AntTarget):
  """ Does absolutely nothing. Optionally allows required targets
      and can serve as a "buffer" between its dependencies and
      other targets that depend on it, by declaring that it has
      outputs, classpath elements, etc, that are actually built
      by its requred targets

      required_targets   Opt - (as above)
      classpath_elements Opt - (as above)
      sources           Opt - (as above)
      outputs           Opt - (as above)
      standalone_exempt  Opt - (see JarTarget)

      By default, this is a build-phase target
  """

  def __init__(self, required_targets=None, classpath_elements=None,
      sources=None, outputs=None, standalone_exempt=False):
    AntTarget.__init__(self)
    self.required_targets = required_targets
    self.classpath_elements = classpath_elements
    self.sources = sources
    self.outputs = outputs
    self.standalone_exempt = standalone_exempt


  def generates_preamble(self):
    return not self.isEmpty()

  def isEmpty(self):
    return self.required_targets == None or len(self.required_targets) == 0

  def isStandaloneExempt(self):
    return self.standalone_exempt

  def language(self):
    # Assume that all the targets are of the same language. An unfortunate
    # oversimplification. TODO(aaron) - Make this more sane.
    if self.isEmpty():
      return None
    else:
      return self.getTargetByName(self.required_targets[0]).language()

  def get_ant_rule_map(self):
    if not self.isEmpty():
      return {
        "build"   : self.getSafeName() + "-build",
        "default" : self.getSafeName() + "-build",
      }
    else:
      return { }

  def antRule(self, rule):
    """ generates the XML to put in the buildfile
        for the ant rule """

    if rule == "preamble":
      return self.output_target_preamble()

    (mainName, ruleType) = self.splitRuleName(rule)
    # all we do is depend on what the user says; no actual action
    text = "<target name=\"" + rule + "\" "
    depAntRules = self.getAntDependencies("build")
    text = text + depAntRules + " />\n"
    return text

  def outputPaths(self):
    """ return whatever the user claimed the outputs are """
    if self.outputs == None:
      return []
    else:
      return self.outputs

  def intermediatePaths(self):
    """ Return whatever our transitive dependencies generate """

    paths = []

    for dep in self.required_targets:
      target = self.getTargetByName(dep)
      if hasattr(target, "intermediatePaths"):
        paths.extend(target.intermediatePaths())

    return paths


  def intermediatePathsForLang(self, lang):
    """ Return whatever our transitive dependencies generate """

    paths = []

    for dep in self.required_targets:
      target = self.getTargetByName(dep)
      if hasattr(target, "intermediatePathsForLang"):
        paths.extend(target.intermediatePathsForLang(lang))

    return paths



class ProjectList(Target):
  """ Represents a no-operation "target" that just identifies
      more paths to projects that should participate in the build
      processed. Use for top-level Targets files that just point
      to subpaths.

      Parameters:
      required_targets Req - List of projects/dirs containing Targets files
  """

  def __init__(self, required_targets):
    Target.__init__(self)
    self.required_targets = required_targets

  def isEmpty(self):
    return True


class ThriftTarget(AntTarget):
  """ Runs thrift on a .thrift file to generate interfaces
      to the protocol as genfiles

      Parameters:
      thrift_file      Req - Filename of the .thrift file to process
      languages       Req - List of languages for which we should generate.
                            Legal values are "py", "java", "html"
      required_targets Opt - (as above)
  """

  def __init__(self, thrift_file, languages, required_targets=None):
    AntTarget.__init__(self)
    self.thrift_file = thrift_file
    self.languages = languages
    self.required_targets = required_targets

  def language(self):
    return "thrift" # TODO: does this matter? It's technically many languages
                    # but we don't support a list here...

  def thrift_filePackageName(self):
    """ thrift compiles into a python package with the same name as the
        .thrift file (without the extension). Return this name based on
        the value of 'thrift_file' """

    filename = os.path.basename(self.thrift_file)
    try:
      dotPos = filename.index(".")
      return filename[0:dotPos]
    except ValueError:
      # no '.' in the name. return the whole basename
      return filename

  def get_ant_rule_map(self):
    return {
      "build" : self.getSafeName() + "-build",
      "clean" : self.getSafeName() + "-clean",
      "default" : self.getSafeName() + "-build"
    }

  def antRule(self, rule):
    """ generates the XML to put in the buildfile
        for the ant rule """

    (mainName, ruleType) = self.splitRuleName(rule)

    if ruleType == "clean":
      return self.cleanRule(rule)

    text = "<target name=\"" + rule + "\" "
    depAntRules = self.getAntDependencies(ruleType)
    text = text + depAntRules + ">\n"

    intermediateDir = self.getIntermediatePath()
    text = text + "  <mkdir dir=\"" + intermediateDir + "\" />\n"

    text = text + "  <delete file=\"" + intermediateDir + os.sep \
        + "status.file\" />\n"
    text = text + "  <dependset>\n"
    text = text + "    <srcfilelist>\n"
    text = text + "      <file name=\"" + self.thrift_file + "\" />\n"
    text = text + "    </srcfilelist>\n"
    text = text + "    <targetfileset"
    text = text + "      dir=\"" + intermediateDir + "\""
    text = text + "      includes=\"**/*\" />\n"
    text = text + "  </dependset>\n"
    text = text + "  <copy todir=\"" + intermediateDir + "\">\n"
    text = text + "    <fileset dir=\"" + intermediateDir + "\"" \
        + " includes=\"*.java\" />\n"
    text = text + "    <mapper type=\"merge\" to=\"status.file\" />\n"
    text = text + "  </copy>\n"
    text = text + "  <available property=\"" + rule + "-uptodate\"\n"
    text = text + "    file=\"" + intermediateDir + os.sep \
        + "status.file\" />\n"

    text = text + "  <if name=\"" + rule + "-uptodate\" exists=\"False\">\n"

    text = text \
        + "  <exec executable=\"thrift\" dir=\"" + self.getInputDirectory() \
        + "\" failonerror=\"true\">\n"
    text = text + "    <arg value=\"-o\"/>\n"
    text = text + "    <arg value=\"" + intermediateDir + "\" />\n"

    for lang in self.languages:
      text = text + "    <arg value=\"--gen\"/>\n"
      text = text + "    <arg value=\"" + lang + "\"/>\n"

    real_thrift_file = self.normalize_user_path(self.thrift_file)
    text = text + "    <arg value=\"" + real_thrift_file + "\"/>\n"
    text = text + "  </exec>\n"
    text = text + "  </if>\n"
    text = text + "</target>\n"
    return text

  def getIntermediatePath(self):
    """ return the path where the thrift output goes """
    return "${genfiles-outdir}/" + self.getBuildDirectory()

  def get_assembly_dir(self):
    return self.getIntermediatePath()

  def intermediatePathsForLang(self, lang):
    """ return paths specific to a given language """

    def listContains(lst, what):
      try:
        lst.index(what)
        return True
      except ValueError:
        return False

    # TODO: Support more than these two languages for now.
    if lang == "python" and listContains(self.languages, "py"):
      return [ self.getIntermediatePath() + "/gen-py/" \
          + self.thrift_filePackageName() ]
    elif lang == "java" and listContains(self.languages, "java"):
      return [ self.getIntermediatePath() + "/gen-java/" ]

  def intermediatePaths(self):
    """ return paths to external clients """

    outList = []
    for lang in self.languages:
      outList.append(self.getIntermediatePath() + "/gen-" + lang)

    return outList

  def cleanRule(self, rule):
    """ a rule to clean the genfiles output """
    text = "<target name=\"" + rule + "\">\n"
    dest_dir = self.getIntermediatePath()
    text = text + "  <delete dir=\"" + dest_dir + "\" />\n"
    text = text + "</target>\n"
    return text


class CupTarget(AntTarget):
  """ Runs java_cup on a .cup file to create parser outputs
      as genfiles for compilation into a jar.

      Parameters:
      cupFile            Req - Filename of the .cup file to process
      parser             Opt - Class name of the parser to generate
      symbols            Opt - Class name of the symbol table to generate
      required_targets    Opt - (as above)
      classpath_elements  Opt - (as above); auto-includes java_cup.jar
      java_options        Opt - arguments to pass to Java VM
  """

  def __init__(self, cupFile, parser="parser.java", symbols="sym.java",
      required_targets=None, classpath_elements=None, java_options=None):

    AntTarget.__init__(self)
    self.cupFile = cupFile
    self.parser = parser
    self.symbols = symbols
    self.required_targets = required_targets
    self.classpath_elements = classpath_elements
    self.java_options = java_options


  def getClassPathElements(self):
    classPathsOut = [ "${cup-jar}" ]
    if self.classpath_elements != None:
      classPathsOut.extend(self.classpath_elements)
    return classPathsOut


  def language(self):
    return "java"


  def get_ant_rule_map(self):
    return {
      "build" : self.getSafeName() + "-build",
      "clean" : self.getSafeName() + "-clean",
      "default" : self.getSafeName() + "-build"
    }


  def antRule(self, rule):
    """ generates the XML to put in the buildfile
        for the ant rule """

    (mainName, ruleType) = self.splitRuleName(rule)

    if ruleType == "clean":
      return self.cleanRule(rule)

    text = "<target name=\"" + rule + "\" "
    depAntRules = self.getAntDependencies(ruleType)
    text = text + depAntRules + ">\n"

    intermediateDir = self.getIntermediatePath()
    text = text + "  <mkdir dir=\"" + intermediateDir + "\" />\n"

    text = text + "  <delete file=\"" + intermediateDir + os.sep \
        + "status.file\" />\n"
    text = text + "  <dependset>\n"
    text = text + "    <srcfilelist>\n"
    text = text + "      <file name=\"" + self.cupFile + "\" />\n"
    text = text + "    </srcfilelist>\n"
    text = text + "    <targetfileset"
    text = text + "      dir=\"" + intermediateDir + "\""
    text = text + "      includes=\"*.java\" />\n"
    text = text + "  </dependset>\n"
    text = text + "  <copy todir=\"" + intermediateDir + "\">\n"
    text = text + "    <fileset dir=\"" + intermediateDir + "\"" \
        + " includes=\"*.java\" />\n"
    text = text + "    <mapper type=\"merge\" to=\"status.file\" />\n"
    text = text + "  </copy>\n"
    text = text + "  <available property=\"" + rule + "-uptodate\"\n"
    text = text + "    file=\"" + intermediateDir + os.sep \
        + "status.file\" />\n"

    text = text + "  <if name=\"" + rule + "-uptodate\" exists=\"False\">\n"

    text = text + \
        "  <java jar=\"${cup-jar}\" fork=\"true\" failonerror=\"true\">\n"
    text = text + "    <arg line=\"-destdir '" + intermediateDir + "'\"/>\n"
    if None != self.parser:
      text = text + "    <arg line=\"-parser " + self.parser + "\"/>\n"
    if None != self.symbols:
      text = text + "    <arg line=\"-symbols " + self.symbols + "\"/>\n"

    full_cup_file = self.normalize_user_path(self.cupFile)
    text = text + "    <arg line=\"" + full_cup_file + "\"/>\n"

    if None != self.java_options:
      text = text + "    <jvmarg line=\"" + self.java_options + "\"/>\n"

    text = text + "    <classpath>\n"
    text = text + "      <path refid=\"" + self.getSafeName() + ".classpath\" />\n"
    depClassPaths = self.getDependencyClassPaths(ruleType, True,
        AllDependencies)
    if depClassPaths != None:
      for elem in depClassPaths:
        text = text + "      <path refid=\"" + elem + "\" />\n"
    text = text + "    </classpath>\n"

    text = text + "  </java>\n"
    text = text + "  </if>\n"
    text = text + "</target>\n"
    return text

  def getIntermediatePath(self):
    """ return the path where the cup output goes """
    return "${genfiles-outdir}/" + self.getBuildDirectory()

  def intermediatePaths(self):
    """ return paths to external clients """
    return [ self.getIntermediatePath() ]

  def get_assembly_dir(self):
    return self.getIntermediatePath()

  def cleanRule(self, rule):
    """ a rule to clean the genfiles output """
    text = "<target name=\"" + rule + "\">\n"
    dest_dir = self.getIntermediatePath()
    text = text + "  <delete dir=\"" + dest_dir + "\" />\n"
    text = text + "</target>\n"
    return text


class JFlexTarget(AntTarget):
  """ Runs JFlex on a .flex file to create lexer outputs
      as genfiles for compilation into a jar.

      Parameters:
      flexFile           Req - Filename of the .flex file to process
      required_targets    Opt - (as above)
      classpath_elements  Opt - (as above); auto-includes jflex-jar
      java_options        Opt - arguments to pass to Java VM
  """

  def __init__(self, flexFile, required_targets=None,
      classpath_elements=None, java_options=None):

    AntTarget.__init__(self)
    self.flexFile = flexFile
    self.required_targets = required_targets
    self.classpath_elements = classpath_elements
    self.java_options = java_options


  def getClassPathElements(self):
    classPathsOut = [ "${jflex-jar}" ]
    if self.classpath_elements != None:
      classPathsOut.extend(self.classpath_elements)
    return classPathsOut

  def language(self):
    return "java"


  def get_ant_rule_map(self):
    return {
      "build" : self.getSafeName() + "-build",
      "clean" : self.getSafeName() + "-clean",
      "default" : self.getSafeName() + "-build"
    }


  def antRule(self, rule):
    """ generates the XML to put in the buildfile
        for the ant rule """

    (mainName, ruleType) = self.splitRuleName(rule)

    if ruleType == "clean":
      return self.cleanRule(rule)

    text = "<target name=\"" + rule + "\" "
    depAntRules = self.getAntDependencies(ruleType)
    text = text + depAntRules + ">\n"

    intermediateDir = self.getIntermediatePath()

    text = text + "  <mkdir dir=\"" + intermediateDir + "\" />\n"
    text = text + "  <delete file=\"" + intermediateDir + os.sep \
        + "status.file\" />\n"
    text = text + "  <dependset>\n"
    text = text + "    <srcfilelist>\n"
    text = text + "      <file name=\"" + self.flexFile + "\" />\n"
    text = text + "    </srcfilelist>\n"
    text = text + "    <targetfileset"
    text = text + "      dir=\"" + intermediateDir + "\""
    text = text + "      includes=\"*.java\" />\n"
    text = text + "  </dependset>\n"
    text = text + "  <copy todir=\"" + intermediateDir + "\">\n"
    text = text + "    <fileset dir=\"" + intermediateDir + "\"" \
        + " includes=\"*.java\" />\n"
    text = text + "    <mapper type=\"merge\" to=\"status.file\" />\n"
    text = text + "  </copy>\n"
    text = text + "  <available property=\"" + rule + "-uptodate\"\n"
    text = text + "    file=\"" + intermediateDir + os.sep \
        + "status.file\" />\n"
    text = text + "  <if name=\"" + rule + "-uptodate\" exists=\"False\">\n"

    text = text + \
        "  <java jar=\"${jflex-jar}\" fork=\"true\" failonerror=\"true\">\n"
    text = text + "    <arg line=\"-d '" + intermediateDir + "'\"/>\n"

    full_flex_file = self.normalize_user_path(self.flexFile)
    text = text + "    <arg line=\"" + full_flex_file + "\"/>\n"

    if None != self.java_options:
      text = text + "    <jvmarg line=\"" + self.java_options + "\"/>\n"

    text = text + "    <classpath>\n"
    # source files generated by cup are included in classpath here
    for src in self.getDependencySourcesForLang("java"):
      text = text + "      <pathelement path=\"" + src + "\" />\n"

    text = text + "      <path refid=\"" + self.getSafeName() + ".classpath\" />\n"
    depClassPaths = self.getDependencyClassPaths(ruleType, True,
        AllDependencies)
    if depClassPaths != None:
      for elem in depClassPaths:
        text = text + "      <path refid=\"" + elem + "\" />\n"
    text = text + "    </classpath>\n"

    text = text + "  </java>\n"
    text = text + "  </if>\n"
    text = text + "</target>\n"
    return text

  def getIntermediatePath(self):
    """ return the path where the cup output goes """
    return "${genfiles-outdir}/" + self.getBuildDirectory()

  def intermediatePaths(self):
    """ return paths to external clients """
    return [ self.getIntermediatePath() ]

  def getFullBuildPath(self):
    return self.getIntermediatePath()

  def cleanRule(self, rule):
    """ a rule to clean the genfiles output """
    text = "<target name=\"" + rule + "\">\n"
    dest_dir = self.getIntermediatePath()
    text = text + "  <delete dir=\"" + dest_dir + "\" />\n"
    text = text + "</target>\n"
    return text



def defaultTarget(someTarget):
  """ sets 'someTarget' as the default target in this
      Targets file."""

  import metamake.buildfile as buildfile
  buildfile.getCurBuildFile().defaultTarget = someTarget

