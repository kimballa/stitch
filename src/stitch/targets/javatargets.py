# (c) Copyright 2009 Cloudera, Inc.
#
# javatargets.py
#
# Defines the JarTarget, JavaTarget, JavaTestTarget classes
# and the JavaBaseTarget abstract class

import os

import stitch.paths as paths
from   stitch.targets.targeterror import TargetError
from   stitch.targets.target import *
from   stitch.targets.anttarget import *
import stitch.antgenerator as antgenerator



class JavaBaseTarget(AntTarget):
  """ Contains common code for JarTarget, JavaTestTarget """

  def __init__(self):
    AntTarget.__init__(self)


  def generates_preamble(self):
    return True


  def get_sources(self):
    return self.force(self.sources)


  def java_preamble(self):
    """ Emit named path objects for classpath and outputs """
    return self.output_target_preamble()


  def doc(self, rule, mainName, build_rule_name):
    """ Run javadoc """

    outdir = "${docs-outdir}/" + self.getBuildDirectory()
    text = ""

    # uptodate rule to check whether to build javadoc in the first place
    text = text + "<target name=\"" + rule + "-uptodate\" depends=\"init\">\n"
    text = text + "  <uptodate property=\"" + rule + "-is-uptodate\">\n"
    for src in self.get_sources():
      text = text + "    <srcfiles dir=\"" + self.normalize_user_path(src) + "\">\n"
      text = text + "      <include name=\"**/*.java\" />\n"
      text = text + "      <include name=\"**/*.html\" />\n"
      text = text + "    </srcfiles>\n"
    text = text + "    <mapper type=\"merge\" to=\"" + outdir + "/index.html\" />\n"
    text = text + "  </uptodate>\n"
    text = text + "</target>\n"

    # Now emit the actual rule
    text = text + "<target name=\"" + rule + "\" depends=\"" + build_rule_name + "," \
        + rule + "-uptodate\" unless=\"" + rule + "-is-uptodate\">\n"
    text = text + "  <mkdir dir=\"" + outdir + "\"/>\n"
    text = text + "  <javadoc failonerror=\"true\"\n"
    if self.javadoc_overview != None:
      text = text + "  overview=\"" + self.normalize_user_path(self.javadoc_overview) + "\"\n"

    text = text + "  author=\"true\" version=\"true\" use=\"true\"\n"
    title = self.getCanonicalName() + " API"
    text = text + "  windowtitle=\"" + title + "\" doctitle=\"" + title + "\"\n"
    text = text + "  destdir=\"" + outdir + "\">\n"

    for src in self.get_sources():
      text = text + "    <fileset dir=\"" + self.normalize_user_path(src) + "\">\n"
      text = text + "      <include name=\"**/*.java\" />\n"
      text = text + "      <include name=\"**/*.html\" />\n"
      text = text + "    </fileset>\n"

    text = text + "    <classpath>\n"
    text = text + "      <path refid=\"" + self.getSafeName() + ".classpath\" />\n"

    depClassPaths = self.getDependencyClassPaths("build", True)
    if depClassPaths != None:
      for elem in depClassPaths:
        text = text + "      <path refid=\"" + elem + "\" />\n"
    text = text + "    </classpath>\n"
    text = text + "  </javadoc>\n"
    text = text + "</target>\n"
    return text


  def javacCore(self, ruleType, dest_dir, debug):
    """ generate the <javac> command at the heart of compileRule() """

    text = "<javac destdir=\"" + dest_dir + "\""

    if debug:
      text = text + " debug=\"on\" debuglevel=\"vars,lines\""

    text = text + ">\n"

    for src in self.get_sources():
      srcpath = self.normalize_user_path(src)
      text = text + "  <src path=\"" + srcpath + "\" />\n"

    for src in self.getDependencySourcesForLang("java"):
      text = text + "  <src path=\"" + src + "\" />\n"

    text = text + "  <classpath>\n"
    text = text + "    <path refid=\"" + self.getSafeName() + ".classpath\" />\n"
    depClassPaths = self.getDependencyClassPaths(ruleType, True, AllDependencies)
    if depClassPaths != None:
      for elem in depClassPaths:
        text = text + "    <path refid=\"" + elem + "\" />\n"
    text = text + "  </classpath>\n"

    if None != self.javac_options:
      text = text + "  <compilerarg line=\"" + self.javac_options + "\"/>\n"
    if debug and None != self.debug_javac_options:
      text = text + "  <compilerarg line=\"" + self.debug_javac_options + "\"/>\n"
    if not debug and None != self.build_javac_options:
      text = text + "  <compilerarg line=\"" + self.build_javac_options + "\"/>\n"
    if debug: # check deprecation in debug mode
      text = text + "  <compilerarg line=\"-deprecation\"/>\n"

    text = text + "</javac>\n"

    return text



  def cleanRule(self, rule, mainName):
    """ generate a clean command """

    text = "<target name=\"" + rule + "\">\n"
    dest_dir = self.get_assembly_dir()
    text = text + "  <delete dir=\"" + dest_dir + "\" />\n"
    text = text + "</target>\n"
    return text



class JarTarget(JavaBaseTarget):
  """ Builds a .jar out of a set of .java files.
      Parameters:
      jar_name           Req - Name of the jar file (e.g., "foo.jar")
      sources           Req - List of relative paths to source code
                              If these are directories, they are recursively
                              included
      required_targets   Opt - List of other projects/dirs containing Targets
                              files required by this project. This is always
                              relative to the root of the src build tree
      classpath_elements Opt - A list of paths that should be added
                              to the classpath when compiling/running
                              this jar
      main_class_name     Opt - String: Class containing main method
      javac_options      Opt - String: opts to pass to the javac command line
      build_javac_options Opt - String: opts for javac in 'build' mode only
      debug_javac_options Opt - String: opts for javac in 'debug' mode only
      data_paths         Opt - paths containing data which need to
                              be included in the output jar
      standalone        Opt - boolean: if True, then any dependency jars
                              are put into this jar in a lib/ directory,
                              except those which are set as standalone_exempt.
                              (defaults to False)
      standalone_exempt  Opt - boolean: if True, then standalone jars
                              depending on this one do not get a copy of
                              this, or its dependencies.
      javadoc_overview   Opt - overview.html file to use for javadoc.
  """

  def __init__(self, jar_name, sources, required_targets=None,
      classpath_elements=None, main_class_name=None, javac_options=None,
      build_javac_options=None, debug_javac_options=None,
      data_paths=None, standalone=False, standalone_exempt=False,
      javadoc_overview=None):
    JavaBaseTarget.__init__(self)
    self.jar_name = jar_name
    self.sources = sources
    self.required_targets = required_targets
    self.classpath_elements = classpath_elements
    self.main_class_name = main_class_name
    self.javac_options = javac_options
    self.build_javac_options = build_javac_options
    self.debug_javac_options = debug_javac_options
    self.data_paths = data_paths
    self.standalone = standalone
    self.standalone_exempt = standalone_exempt
    self.javadoc_overview = javadoc_overview


  def isStandalone(self):
    return self.standalone

  def isStandaloneExempt(self):
    return self.standalone_exempt

  def language(self):
    return "java"

  def get_ant_rule_map(self):
    return {
      "build"          : self.getSafeName() + "-build",
      "default"        : self.getSafeName() + "-build",
      "clean"          : self.getSafeName() + "-clean",
      "findbugs"       : self.getSafeName() + "-findbugs",
      "findbugs-inner" : self.getSafeName() + "-findbugs_inner",
      "checkstyle"     : self.getSafeName() + "-checkstyle",
      "pmd"            : self.getSafeName() + "-pmd",
      "doc"            : self.getSafeName() + "-doc",
    }


  def antRule(self, rule):
    """ generates the XML to put in the buildfile
        for the ant rule """

    if rule == "preamble":
      return self.java_preamble()

    (mainName, ruleType) = self.splitRuleName(rule)

    if ruleType == "clean":
      return self.cleanRule(rule, mainName)
    elif ruleType == "findbugs":
      return self.findbugs_shell(rule, mainName)
    elif ruleType == "findbugs_inner":
      return self.findbugs(rule, mainName)
    elif ruleType == "checkstyle":
      return self.checkstyle(rule, mainName)
    elif ruleType == "pmd":
      return self.pmd(rule, mainName)
    elif ruleType == "doc":
      return self.doc(rule, mainName, mainName + "-build")
    else:
      return self.compileRule(rule, mainName, ruleType)


  def get_assembly_dir(self):
    return "${outdir}/" + self.getBuildDirectory()


  def findbugs(self, rule, mainName):
    """ Generate a command to actually run findbugs """
    text = "<target name=\"" + rule + "\" depends=\"" + mainName + "-build\">\n"

    if self.getCanonicalName().find("thirdparty") != -1:
      text = text + "  <echo message=\"Skipping findbugs for thirdparty target " \
          + self.getCanonicalName() + "\"/>\n"
    else:
      text = text + """  <findbugs home="${findbugs-home}"
      errorProperty="failed" warningsProperty="failed"
      excludeFilter="${findbugs-exclude-filter}"
      output="text" jvmargs="-Xmx512m">\n"""

      for output in self.outputPaths():
        text = text + "    <class location=\"" + output + "\" />\n"

      text = text + "    <auxClasspath>\n"

      classPath = []
      classPath.extend(self.getDependencyClassPaths("build", True))
      classPath.append(self.getSafeName() + ".outputs")
      classPath.append(self.getSafeName() + ".classpath")
      classPath = antgenerator.unique(classPath)

      for elem in classPath:
        text = text + "      <path refid=\"" + elem + "\" />\n"

      text = text + "    </auxClasspath>\n"
      text = text + "  </findbugs>\n"

    text = text + "</target>\n"
    return text

  def findbugs_shell(self, rule, mainName):
    """ Generate a command for the user to run findbugs """

    text = "<target name=\"" + rule + "\" depends=\"" + rule + "_inner\">\n"
    text = text + "  <fail if=\"failed\" message=\"Findbugs found errors.\" />\n"
    text = text + "</target>\n"
    return text

  def checkstyle(self, rule, mainName):
    """ Generate a command for the user to run checkstyle """

    text = ""
    text = text + "<target name=\"" + rule + "\">\n"
    text = text + "  <checkstyle config=\"${checkstyle-config-path}\">\n"
    text = text + "    <fileset dir=\"${basedir}\">\n"
    for src in self.get_sources():
      srcpath = self.normalize_user_path(src, is_dest_path=False, include_basedir=False)
      text = text + "  <include name=\"" + srcpath + "**/*.java\" />\n"
    text = text + """
      <exclude name="thirdparty/*" />
      <exclude name="thirdparty/**" />
      <exclude name="**/thirdparty/*" />
      <exclude name="**/thirdparty/**" />
    </fileset>
  </checkstyle>
</target>"""

    return text


  def pmd(self, rule, mainName):
    """ Generate a command for the user to run pmd """

    text = ""
    text = text + "<target name=\"" + rule + "\">\n"
    text = text + "  <pmd failonerror=\"true\" failOnRuleViolation=\"true\"\n"
    text = text + "    rulesetfiles=\"${pmd-home}/rulesets/basic.xml,\n"
    text = text + "    ${pmd-home}/rulesets/unusedcode.xml\">\n"
    text = text + "    <formatter type=\"text\" toConsole=\"true\" />\n"
    text = text + "    <fileset dir=\"${basedir}\">\n"
    for src in self.get_sources():
      srcpath = self.normalize_user_path(src, is_dest_path=False, include_basedir=False)
      text = text + "  <include name=\"" + srcpath + "**/*.java\" />\n"
    text = text + """
      <exclude name="thirdparty/*" />
      <exclude name="thirdparty/**" />
      <exclude name="**/thirdparty/*" />
      <exclude name="**/thirdparty/**" />
    </fileset>
  </pmd>
</target>"""

    return text


  def compileRule(self, rule, mainName, ruleType):
    """ generate a compile command """

    text = "<target name=\"" + rule + "\" "
    depAntRules = self.getAntDependencies(ruleType)
    text = text + depAntRules + ">\n"

    dest_dir = "${outdir}/" + self.getBuildDirectory()
    text = text + "  <mkdir dir=\"" + dest_dir + "\"/>\n"

    # annoying: javac Ant task will allow you to specify debug="on"
    # and debuglevel="vars" in the parameters, but not as a subtask.
    # therefore, we can't do this easily with a conditional, so we
    # use the manual 'compilerarg'. Boo.
    text = text + "  <if name=\"debug\">\n"
    text = text + self.javacCore(ruleType, dest_dir, True)
    text = text + "    <else>\n"
    text = text + self.javacCore(ruleType, dest_dir, False)
    text = text + "    </else>\n"
    text = text + "  </if>\n"

    text = text + self.copyDataPaths(dest_dir)

    if self.isStandalone():
      # copy all dependencies into the lib/ directory
      classPathComponents = [ self.getSafeName() + ".classpath" ]
      classPathComponents.extend(self.getDependencyClassPaths(ruleType, True, StandaloneDepsOnly))

      if len(classPathComponents) > 0:
        text = text + "  <mkdir dir=\"" + dest_dir + os.sep + "lib\"/>\n"
        text = text + "  <copy todir=\"" + dest_dir + os.sep + "lib\"" \
            + " flatten=\"true\">\n"
        text = text + "    <path>\n"
        for elem in classPathComponents:
          text = text + "    <path refid=\"" + elem + "\"/>\n"
        text = text + "    </path>\n"
        text = text + "  </copy>\n"

    text = text + "  <mkdir dir=\"${jardir}\" />\n"
    text = text + "  <jar destfile=\"${jardir}/" + self.jar_name + "\"\n"
    text = text + "    basedir=\"" + dest_dir + "\">\n"
    if self.main_class_name != None:
      text = text + """
    <manifest>
      <attribute name="Main-Class" value="%(mainclass)s" />
    </manifest>
""" % { "mainclass" : self.force(self.main_class_name) }

    text = text + "  </jar>\n"
    text = text + "</target>\n"
    return text


  def outputPaths(self):
    return [ "${jardir}/" + self.force(self.jar_name) ]



class JavaTarget(AntTarget):
  """ Makes a script which can run a java class.
      Parameters:

      main_jar_target     Req - Name of the target that build the main jar
      main_class_name     Opt - Overrides main_class_name of main_jar_target
      exec_name          Opt - Name of the executable script (defaults to
                              the main class name)
      required_targets   Opt - List of paths/dirs containing other required
                              Targets files
      classpath_elements Opt - List of paths to add to classpath for running
      java_options       Opt - Options to pass to java vm on command line
      data_paths         Opt - Paths containing data which need to be
                              bundled along
  """
  def __init__(self, main_jar_target, main_class_name=None,
      exec_name=None, required_targets=None, classpath_elements=None,
      java_options=None, data_paths=None):
    AntTarget.__init__(self)
    self.main_jar_target = main_jar_target
    self.main_class_name = main_class_name
    self.exec_name = exec_name
    self.required_targets = required_targets
    self.classpath_elements = classpath_elements
    self.java_options = java_options
    self.data_paths = data_paths

    # put main_jar_target into required_targets
    if self.required_targets == None:
      self.required_targets = [ self.main_jar_target ]
    else:
      self.required_targets.append(self.main_jar_target)


  def language(self):
    return "java"


  def generates_preamble(self):
    return True


  def get_ant_rule_map(self):
    return {
      "build"   : self.getSafeName() + "-build",
      "default" : self.getSafeName() + "-build",
      "clean"   : self.getSafeName() + "-clean"
    }


  def antRule(self, rule):

    if rule == "preamble":
      return self.output_target_preamble()

    (mainName, ruleType) = self.splitRuleName(rule)

    if ruleType == "clean":
      return self.cleanRule(rule, mainName)
    else:
      return self.compileRule(rule, mainName, ruleType)


  def cleanRule(self, rule, mainName):
    """ generate a clean command """

    text = "<target name=\"" + rule + "\">\n"
    dest_dir = self.get_assembly_dir()
    text = text + "  <delete dir=\"" + dest_dir + "\" />\n"
    text = text + "</target>\n"
    return text


  def compileRule(self, rule, mainName, ruleType):
    """ generate the build command """

    text = "<target name=\"" + rule + "\" "
    depAntRules = self.getAntDependencies(ruleType, ["java-prereqs"])
    text = text + depAntRules + ">\n"

    # create the output directory
    dest_dir = self.get_assembly_dir()
    text = text + "  <mkdir dir=\"" + dest_dir + "\"/>\n"

    # copy the jar in to this directory
    if self.main_jar_target == None or len(self.main_jar_target) == 0:
      raise TargetError(self, "Target " + self.getCanonicalName() \
          + " does not have the required 'main_jar_target' attribute set.")
    jarTargetObj = self.getTargetByName(self.force(self.main_jar_target))
    if jarTargetObj == None:
      raise TargetError(self, "Target " + self.getCanonicalName() \
          + " cannot find main_jar_target=\"" + self.force(self.main_jar_target) + "\"")
    # this should return a singleton list
    jarFileLst = jarTargetObj.outputPaths()
    if len(jarFileLst) == 0:
      raise TargetError(self, "Target " + self.getCanonicalName() \
          + " with main_jar_target=\"" + self.force(self.main_jar_target) + "\";"
          + " no jar file set in main_jar_target")
    if len(jarFileLst) > 1:
      raise TargetError(self, "Target " + self.getCanonicalName() \
          + " with main_jar_target=\"" + self.force(self.main_jar_target) + "\";"
          + " multiple output files set in main_jar_target. (Are you"
          + " sure this is a JarTarget?)")
    jarFileName = jarFileLst[0]

    text = text + "  <copy todir=\"" + dest_dir + "\" file=\"" \
        + jarFileName + "\"/>\n"

    # copy all dependencies into the lib/ directory.
    # if our main jar is a standlone jar, though, we don't want anything
    # already wrapped into the jar.
    includePolicy = AllDependencies
    if jarTargetObj.isStandalone():
      includePolicy = ExcludeStandaloneChildren
    classPathComponents = [ self.getSafeName() + ".classpath" ]
    classPathComponents.extend(self.getDependencyClassPaths(ruleType, True, includePolicy))

    if len(classPathComponents) > 0:
      text = text + "  <mkdir dir=\"" + dest_dir + os.sep + "lib\"/>\n"
      text = text + "  <copy todir=\"" + dest_dir + os.sep + "lib\"" \
          + " flatten=\"true\">\n"
      text = text + "    <path>\n"
      for elem in classPathComponents:
        text = text + "    <path refid=\"" + elem + "\"/>\n"

      text = text + "    </path>\n"
      text = text + "  </copy>\n"

    # make sure the main jar isn't in its own lib dir.
    jar_base_name = os.path.basename(jarFileName)
    text = text + "  <delete file=\"" + os.path.join(dest_dir, "lib", jar_base_name) + "\"/>\n"

    # copy our data paths over.
    text = text + self.copyDataPaths(dest_dir)

    # finally, make the executable.
    text = text + "  <exec executable=\"${make-java-script}\"\n"
    text = text + "    failonerror=\"true\">\n"
    text = text + "    <arg value=\"--mainclass\"/>\n"
    text = text + "    <arg value=\"" + self.getMainClass() + "\"/>\n"
    text = text + "    <arg value=\"--exec\"/>\n"
    text = text + "    <arg value=\"" + self.getExecName() + "\"/>\n"
    text = text + "    <arg value=\"--dir\"/>\n"
    text = text + "    <arg value=\"" + dest_dir + "\"/>\n"
    if self.java_options != None:
      java_opts = self.force(self.java_options):
      if len(java_opts) > 0:
        text = text + "    <arg value=\"--javaopts\"/>\n"
        text = text + "    <arg value=\"" + java_opts + "\"/>\n"
    text = text + "  </exec>\n"

    text  = text + "</target>\n"
    return text


  def getMainClass(self):
    """ return the name of the main class to invoke """

    if self.main_class_name != None and len(self.force(self.main_class_name)) > 0:
      # we specified our own main class name
      return self.force(self.main_class_name)
    else:
      # get the main class name from the jar target.
      main_target_name = self.force(main_jar_target)
      jar_target = self.getTargetByName(main_target_name)
      if None == jar_target:
        raise TargetError(self, "Could not find jar target: " + main_target-name)
      main_jar_class = getattr(jar_target, "main_class_name", "")
      if main_jar_class == None or len(main_jar_class) == 0:
        raise TargetError(self, "Target " + self.getCanonicalName() \
            + " does not have main_class_name attribute, nor does its"
            + " main jar target, " + jar_target.getCanonicalName())
      return main_jar_class


  def finalClassStep(self, className):
    """ for a class named foo.bar.baz.SomeClass, return "SomeClass" """
    if className == None:
      return ""

    parts = className.split(".")
    return parts[len(parts) - 1]


  def getExecName(self):
    """ get the name to assign to the executable """
    if self.exec_name != None:
      forced = self.force(self.exec_name)
      if len(forced) > 0:
        return forced

    return self.finalClassStep(self.getMainClass())


  def outputPaths(self):
    return [ self.get_assembly_dir() ]


class JavaTestTarget(JavaBaseTarget):
  """ Compiles .java files intended for use with JUnit.
      These files are assumed to not be part of the main jar.
      Parameters:

      sources           Req - (as above)
      main_class_name     Req - name of the test suite to invoke
      required_targets   Opt - (as above)
      classpath_elements Opt - (as above)
      javac_options      Opt - (as above)
      build_javac_options Opt - String: opts for javac in 'build' mode only
      debug_javac_options Opt - String: opts for javac in 'debug' mode only
      java_options       Opt - (as above)
      timeout           Opt - timeout value for JUnit
      data_paths         Opt - paths containing data which need to
                              be present when testing is run
      javadoc_overview   Opt - Overview page for generated javadocs.
  """

  def __init__(self, sources, main_class_name, required_targets=None,
      classpath_elements=None, javac_options=None, build_javac_options=None,
      debug_javac_options=None, java_options=None,
      timeout="${junit-timeout}", data_paths=None,
      javadoc_overview=None):

    JavaBaseTarget.__init__(self)
    self.sources = sources
    self.main_class_name = main_class_name
    self.required_targets = required_targets
    self.classpath_elements = classpath_elements
    self.javac_options = javac_options
    self.build_javac_options = build_javac_options
    self.debug_javac_options = debug_javac_options
    self.java_options = java_options
    self.timeout = timeout
    self.data_paths = data_paths
    self.javadoc_overview = javadoc_overview

  def language(self):
    return "java"

  def get_ant_rule_map(self):
    return {
      "build"      : self.getSafeName() + "-build",
      "clean"      : self.getSafeName() + "-clean",
      "test-inner" : self.getSafeName() + "-test",
      "test"       : self.getSafeName() + "-testshell",
      "default"    : self.getSafeName() + "-testshell",
      "doc"        : self.getSafeName() + "-doc",
    }


  def outputPaths(self):
    """ the .class generation directory is the output path
        of any build target """
    return [ self.get_assembly_dir() ]

  def antRule(self, rule):
    """ generates the XML to put in the buildfile
        for the ant rule """

    if rule == "preamble":
      return self.java_preamble()

    (mainName, ruleType) = self.splitRuleName(rule)

    if ruleType == "clean":
      return self.cleanRule(rule, mainName)
    elif ruleType == "build":
      return self.compileRule(rule, mainName, ruleType)
    elif ruleType == "test":
      return self.testRule(rule, mainName)
    elif ruleType == "testshell":
      return self.testShellRule(rule, mainName)
    elif ruleType == "doc":
      return self.doc(rule, mainName, mainName + "-build")


  def compileRule(self, rule, mainName, ruleType):
    """ generate a compile command """

    text = "<target name=\"" + rule + "\" "
    depAntRules = self.getAntDependencies(ruleType)
    text = text + depAntRules + ">\n"

    dest_dir = self.get_assembly_dir()
    text = text + "<mkdir dir=\"" + dest_dir + "\"/>\n"

    text = text + "  <if name=\"debug\">\n"
    text = text + self.javacCore(ruleType, dest_dir, True)
    text = text + "    <else>\n"
    text = text + self.javacCore(ruleType, dest_dir, False)
    text = text + "    </else>\n"
    text = text + "  </if>\n"

    text = text + self.copyDataPaths(dest_dir)

    text = text + "</target>\n"

    return text


  def testShellRule(self, rule, mainName):
    """ Run the test rule and fail the build if the test fails """

    text = """
<target name="%(rule)s" depends="%(testrule)s">
  <fail if="failed" message="JUnit test %(testname)s failed" />
</target>
""" % { "rule"     : rule,
        "testrule" : mainName + "-test",
        "testname" : self.getCanonicalName()
      }

    return text


  def testRule(self, rule, mainName):
    """ Execute the JUnit test suite """

    dest_dir = self.get_assembly_dir()

    text = "<target name=\"" + rule + "\" depends=\"" \
        + mainName + "-build\" >\n"
    text = text + """<junit printsummary="withOutAndErr"
  fork="on"
  maxmemory="${junit-mem}"
  failureproperty="failed" """
    text = text + "timeout=\"" + self.force(self.timeout) + "\" "
    text = text + "dir=\"" + dest_dir + "\">\n"
    text = text + "  <formatter type=\"brief\" usefile=\"false\" />\n"
    text = text + "  <classpath>\n"

    text = text + "    <pathelement path=\"" + dest_dir + "\" />\n"

    text = text + "    <path refid=\"" + self.getSafeName() + ".classpath\" />\n"

    # get recursive class paths for execution...
    depClassPaths = self.getDependencyClassPaths("test", True, AllDependencies)
    if depClassPaths != None:
      for elem in depClassPaths:
        text = text + "    <path refid=\"" + elem + "\" />\n"
    text = text + "  </classpath>\n"

    if self.java_options != None:
      java_opts = self.force(self.java_options):
      if len(java_opts) > 0:
        text = text + "  <jvmarg line=\"" + java_opts + "\" />\n"

    text = text + "  <test name=\"" + self.force(self.main_class_name) + "\" />\n"
    text = text + "</junit>\n"
    text = text + "</target>\n"

    return text


  def getClassPathElements(self):
    classPathsOut = [ "${junit-jar}" ]
    if self.classpath_elements != None:
      classPathsOut.extend(self.force(self.classpath_elements))
    return classPathsOut


