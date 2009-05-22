# (c) Copyright 2009 Cloudera, Inc.
#
# Classes which take a graph of BuildFiles and
# Targets and generate some output plans; e.g.,
# ant-directed builds, Eclipse workspace generator, etc.

import os

import metamake.generator as generator
import metamake.paths as paths
import metamake.propstack as propstack

def unique(lst):
  """ uniquify a list of strings """
  myDict = {}
  for elem in lst:
    myDict[elem] = ()
  return myDict.keys()


# singleton ant generator
antGenerator = None
def getAntGenerator():
  global antGenerator
  if antGenerator == None:
    antGenerator = AntGenerator()
  return antGenerator

class AntGenerator(generator.Generator):
  """ Generates a build.xml file in the current directory
      suitable for building all Java and Jar-based targets
      in the BuildFile graph.

      Creates the following ant targets:
      build       Compile all sources
      debug       Compiles sources in debug mode
      test        Run unit tests

      checkstyle  Run checkstyle on .java sources
      pmd         Run pmd on .java sources
      findbugs    Run findbugs on output .jar/.class files
      static      Run the above three tools


      Each Java/Jar/JavaTest Target name (if given)
      is its own target name in the build.xml file as
      well; their paths are changed from foo/bar/baz:TargetName
      to foo.bar.baz.TargetName

      For each of these, a separate "*-clean" target
      is created in the buildfile as well.

      This is typically not used as a top-level generator; it is
      created by the BuildGenerator to handle Ant-providing targets.
  """

  def __init__(self):
    generator.Generator.__init__(self)
    self.handle = None # handle to build.xml to write

    # A mapping from str(phase) : list( (target_name, rulename) )
    # e.g., "build" : [ ("//foo", "project-foo-build"), ("//bar", "project-bar-build") ]
    self.rule_map = {}

    # Set to true if there are any python rules.
    self.has_python = False


  def ensureHandle(self):
    if self.handle == None:
      # parse the properties files that govern this build tree
      # to determine the build directory. Then put build.xml in
      # there.
      antprops = propstack.get_properties()

      build_outputs_dir = antprops.getProperty("outsubdir", "build")

      if not os.path.exists(build_outputs_dir):
        os.mkdir(build_outputs_dir)
      self.handle = open(os.path.join(build_outputs_dir, "build.xml"), "w")

  def closeHandle(self):
    if self.handle != None:
      self.handle.close()

  def add_to_phase(self, phase, target_mapping):
    """
        Adds a (targetname, antrulename) tuple--target_mapping--to the
        list of targets for 'phase'.
    """
    try:
      list_for_phase = self.rule_map[phase]
    except KeyError:
      # not present; create a new list.
      list_for_phase = []
      self.rule_map[phase] = list_for_phase

    list_for_phase.append(target_mapping)


  def generate(self, allTargets):

    rule_text = ""
    public_text = ""
    preamble_text = ""

    try:
      # Clear isGenerated marks for this generator.
      for target in allTargets:
        target.clearGenerated()

      # Now do actual generation.
      for target in allTargets:
        # prevent redundant generation of rules for targets w/ multiple names
        if target.isGenerated():
          continue

        if target.generatesAntRules():
          target.markAsGenerated()
          target.validate_arguments()

          if target.language() == "python":
            self.has_python = True

          if target.generates_preamble():
            # Grab the special preamble rule text.
            preamble_text = preamble_text + target.antRule("preamble")

          # get a map from phase |--> rulename for this target
          my_rule_map = target.get_ant_rule_map()
          if my_rule_map != None:
            for rule in unique(my_rule_map.values()):
              rule_text = rule_text + target.antRule(rule)

            for phase in my_rule_map.keys():
              # add the entries in this target's rule_map to the
              # list associated with the complete rule map
              tuple = (target.getCanonicalName(), my_rule_map[phase])
              self.add_to_phase(phase, tuple)

      # we handle cleaning of all python all-at-once with a rule
      # inserted by the generator, not the targets themselves.
      if self.has_python:
        tuple = ("___special_no_target", "python-clean")
        self.add_to_phase("clean", tuple)

        tuple = ("___special_no_target", "python-build")
        self.add_to_phase("build", tuple)

      # the top-level production rules also depend on the init rule;
      # this must run first. (it will force a new metamake if needed)
      tuple = ("___special_no_target", "init")
      self.add_to_phase("build", tuple)
      self.add_to_phase("test", tuple)

      # now generate the top-level rules that depend on all the
      # specific instances.
      for phase in self.rule_map.keys():
        public_text = public_text + self.generate_phase(phase)

      public_text = public_text + "\n\n<!-- private targets follow -->\n\n"

    finally:
      if len(rule_text) > 0:
        self.ensureHandle()
        self.handle.write(self.antHeader())
        self.handle.write(self.metamakeRule())
        self.handle.write(self.release_version_rule())
        self.handle.write(public_text)
        self.handle.write(preamble_text)
        self.handle.write(rule_text)
        self.handle.write(self.antFooter())
        self.closeHandle()

  def metamakeRule(self):
    """ returns a rule that runs metamake if one of the Targets files
        has been updated since this build.xml file """

    # lazy import to defeat circularity.
    import metamake.buildfile as buildfile

    text = """
<target name="metamake-uptodate">
  <uptodate property="metamake.up-to-date" targetfile="${outdir}/build.xml">
    <srcfiles dir="${basedir}">
      <include name="%(targetsfile)s" />
      <include name="*/%(targetsfile)s" />
      <include name="**/%(targetsfile)s" />
      <exclude name="${outdir}/*" />
      <exclude name="${outdir}/**" />
    </srcfiles>
  </uptodate>
</target>
<target name="metamake-refresh" depends="metamake-uptodate"
    unless="metamake.up-to-date">
  <!-- if not up-to-date and not disallow-refresh, do rebuild -->
  <if name="metamake-disallow-refresh">
    <else>
      <exec executable="${metamake-exec}" failonerror="true"
        dir="${basedir}"/>
      <fail message="metamake has recompiled build.xml; run build again"/>
    </else>
  </if>
</target>
""" % { "targetsfile" : buildfile.DEFAULT_BUILD_FILENAME }
    return text

  def release_version_rule(self):
    """ If the 'release' property is declared and set to true, then we
        build version strings as-is. Otherwise, we append "-test" to
        everything.

        This rule is depended upon by all VerStringTarget entities.
    """

    return """
<target name="release-version">
  <if name="release">
    <property name="test-suffix" value="" />
    <property name="version-subdir" value="release" />
    <else>
      <property name="test-suffix" value="-test" />
      <property name="version-subdir" value="test" />
    </else>
  </if>
</target>
"""
  def getBuildScriptMap(self, allTargets):
    """ given all Target objects, map their canonical name to the
        build script name. """

    text = ""

    for target in allTargets:
      if target.generatesAntRules():
        ant_map = target.get_ant_rule_map()
        if ant_map == None:
          continue

        # The canonical name will be something like //projects/Foo.
        # For path auto-complete sanity, add an entry without the
        # leading '//'.
        # If the canonical name includes a colon (e.g., //projects/Foo:subtarget),
        # then we insert a '/' before the colon too
        target_name = paths.dequalify(target.getCanonicalName())
        try:
          target_name.index(":")
          # found the colon
          trail_slash_target = target_name.replace(":", os.sep + ":")
        except ValueError:
          # no colon; just tack the slash on the end
          trail_slash_target = target_name + os.sep

        # Emit the lookup table entries.
        for phase in ant_map.keys():
          ant_rule = ant_map[phase]
          text = text + """
ant_map[("%(phase)s", "%(target)s")] = "%(ant_rule)s"
ant_map[("%(phase)s", "%(trail_slash_target)s")] = "%(ant_rule)s"
ant_map[("%(phase)s", "//%(target)s")] = "%(ant_rule)s"
ant_map[("%(phase)s", "//%(trail_slash_target)s")] = "%(ant_rule)s"
""" % { "phase" : phase,
        "target" : target_name,
        "trail_slash_target" : trail_slash_target,
        "ant_rule" : ant_rule }

    return text




  def antHeader(self):
    """ return the preamble at the top of the build.xml file """
    text = """<!-- (c) Copyright 2009 Cloudera, Inc. -->
<!-- ******* AUTOGENERATED *******
     DO NOT MODIFY THIS FILE - Recreate with metamake
     Note: While it is possible to run ant directly on this
     file, the recommended method to build targets is via
     the build script in the srcroot (one level up from here)
-->
<project name="world" default="default" basedir="..">
  <property file="my.properties" />
  <property file="build.properties" />
  <property file="/etc/metamake/metamake-config.properties" />

  <description>
    This is the master Ant Buildfile for the Cloudera workspace
  </description>

  <!-- include task definitions -->
  <taskdef resource="checkstyletask.properties"
    classpath="${checkstyle-jar}" />
  <taskdef name="findbugs"
    classname="edu.umd.cs.findbugs.anttask.FindBugsTask"
    classpath="${findbugs-home}/lib/findbugs-ant.jar" />
  <taskdef name="pmd"
    classname="net.sourceforge.pmd.ant.PMDTask"
    classpath="${pmd-home}/lib/pmd-4.2.2.jar" />
  <taskdef name="if" classname="ise.antelope.tasks.IfTask"
    classpath="${metamake-java-libs}/AntelopeTasks_3.4.5.jar" />

  <property environment="env"/>

  <!-- public targets -->
  <target name="clean-jars"
    description="Delete jars built from our sources">
    <delete dir="${jardir}" />
  </target>
  <target name="clean-all"
    description="Remove all possible outputs">
    <delete dir="${outdir}" />
  </target>
  <target name="debug" description="Build in debug mode">
    <antcall target="build">
      <param name="debug" value="True" />
    </antcall>
  </target>
  <target name="java-prereqs" />
  <!-- init rule: everything depends on init so that it runs first -->
  <target name="init" depends="metamake-refresh" />
"""

    if self.has_python:
      text = text + """
    <target name="python-clean" description="Clean python sources">
      <delete dir="${python-outdir}" />
    </target>
    <target name="python-prereqs">
    </target>
  """

    return text


  def antFooter(self):
    """ return the footer at the bottom of the build.xml file """
    return """
</project>
"""

  def generate_phase(self, phase):
    """ top-level rules don't do anything themselves; they just
        depend on a series of lower-level rules """


    str = "<target name=\"" + phase + "\" depends=\""
    first = True
    if self.rule_map.has_key(phase + "-inner"):
      # top-level target depends on the "inner" production rule
      lookup_phase = phase + "-inner"
    else:
      lookup_phase = phase

    for (target, dep) in self.rule_map[lookup_phase]:
      if not first:
        str = str + ","
      first = False
      str = str + dep
    str = str + "\"\n"
    str = str + "description=\"\">\n"

    # special-case handling for some phases is done here:
    if phase == "test" or phase == "python-test":
      # unit test rule requires checking for a failure condition
      str = str + " <fail message=\"Unit tests failed\" if=\"failed\" />\n"
    elif phase == "python-build":
      str = str + """
        <exec executable="python" failonerror="true">
          <arg file="${python-compiler}" />
          <arg value="${python-outdir}" />
        </exec>
      """
    elif phase == "findbugs":
      str = str + " <fail message=\"Findbugs encountered errors\" if=\"failed\" />\n"

    str = str + "</target>\n"
    return str

  def getTopLevelRules(self):
    """ Return a list of the names of rules that we introduce
        into the top-level script """

    phases = self.rule_map.keys()
    rules = []
    for phase in phases:
      if not phase.endswith("-inner"):
        rules.append(phase)

    if self.has_python:
      rules.append("python-clean")
    return rules


  def getTopLevelScript(self, allTargets):
    """ Return the top-level script steps to put into
        the main 'build' script to run ant generated actions """

    antprops = propstack.get_properties()
    build_dir = antprops.getProperty("outsubdir", "build")

    text = """

def formatProperties():
  # return properties definition string from the user:
  global props
  propStr = ""
  for prop in props:
    propStr = propStr + "'" + prop + "' "
  return propStr

ant_map = {}

# run anything from ant
def run_ant_target(ant_target):
  # Hack - Ant 1.7.1 on dev server doesn't seem to respect its
  # own classpath with respect to JUnit and ant.jar. So we're
  # hardcoding it in here.
  # TODO(aaron): Remove this hard-coded path dependency.
  if os.path.exists("/usr/share/ant/lib/ant.jar"):
    classpath = os.getenv("CLASSPATH", "")
    if len(classpath) > 0 and not classpath.endswith(":"):
      classpath = classpath + ":"
    classpath = classpath + "/usr/share/ant/lib/ant.jar"
    os.environ["CLASSPATH"] = classpath
  callString = "ant -f %(BUILD_DIR)s/build.xml " + formatProperties() + ant_target
  ret = os.system(callString)
  if ret > 0:
    sys.exit(1)


def ant_phase(phase):
  run_ant_target(phase)
  sys.exit(0)

def ant_topLevelAnt(phase, target):
  global ant_map, lookup_only, cwd, common_path

  if not target.startswith(os.sep):
    # This is not guaranteed to be an absolute target.
    # Try it relative to the build root (the build script's path).
    target_parts = target.split(":")
    abs_name_part = os.path.abspath(os.path.join(cwd, target_parts[0]))
    abs_target = abs_name_part[len(common_path):]
    if len(target_parts) > 1:
      abs_target += ":" + ":".join(target_parts[1:])
    try:
      ant_target = ant_map[(phase, abs_target)]
    except KeyError:
      # Couldn't find that. Try it as an absolute.
      ant_target = ant_map[(phase, target)]
  else:
    # Definitely an absolute target.
    ant_target = ant_map[(phase, target)]

  if lookup_only:
    # lookup succeeded
    return True
  else:
    run_ant_target(ant_target)

target_handlers.append(ant_topLevelAnt)
phase_handlers.append(ant_phase)
""" % { "BUILD_DIR" : build_dir }

    text = text + self.getBuildScriptMap(allTargets)

    return text



