# (c) Copyright 2009 Cloudera, Inc.
#
# Eclipse workspace generator

import os

import metamake.paths as paths
import metamake.generator as generator
from metamake.util.antproperties import AntProperties


class EclipseGenerator(generator.Generator):
  """ Generates an eclipse workspace that handles all
      Java-based targets in the graph.

      Will also execute the .eclipseHook() method, if
      present, of every target it can find, whether or
      not it is a straight-up java module. This allows
      external/thirdparty modules to be included in
      the Eclipse workspace.
  """

  def __init__(self):
    generator.Generator.__init__(self)
    self.workspacePath = "workspace" + os.sep

    # load ant build properties to reconcile classpath elements.
    self.properties = AntProperties()
    self.properties.setProperty("basedir", ".")
    if os.path.exists("my.properties"):
      handle = open("my.properties")
      self.properties.load(handle);
      handle.close()
    if os.path.exists("global.properties"):
      handle = open("global.properties")
      self.properties.load(handle)
      handle.close()

    # we're not allowed to introduce dependencies against other
    # python projects in the default builder because it must
    # bootstrap easily. But we can do our imports here.
    import metamake.util.dirutils as dirutils
    import metamake.util.oldshell as shell

    self.dirutils = dirutils
    self.shell = shell


  def isPublic(self):
    return True

  def getDescription(self):
    return """EclipseGenerator    Generates an Eclipse workspace that covers
                    all Java-based targets."""

  def generate(self, allTargets):

    print "Creating workspace in " + self.workspacePath + " ..."

    # coalesce all the targets into a dictionary mapping
    # projName -> (target list)
    # Each projName represents a Targets file which contains at least
    # one Java-based target.
    projects = {}

    for target in allTargets:
      if target.language() == "java" or hasattr(target, "eclipseHook"):
        build_filePath = target.getBuildFile().getBuildFileDirectory()
        try:
          projects[build_filePath].append(target)
        except KeyError:
          projects[build_filePath] = [ target ]
        target.markAsGenerated()

    for projName in projects.keys():
      targets = projects[projName]
      self.makeProject(projName, targets, projects)


  def hostOsPath(self, path):
    """ convert a path to the host OS's representation """

    if os.getenv("OS", "") == "Windows_NT":
      # we're in cygwin, but eclipse runs under windows. Cygpath it.
      lines = self.shell.shLines( \
          "cygpath -a -m '" + path + "'", self.shell.emptyFlags())
      if len(lines) == 0:
        raise GeneratorError("Could not run cygpath on cygwin system?")
      return lines[0].strip()
    else:
      return path

  def fullPath(self, projName, src):
    """ return full path to a source folder """

    thePath = os.path.join(os.getcwd(), projName, src)
    return self.hostOsPath(thePath)


  def getBuildRoot(self):
    """ return the build root, as seen by eclipse. """

    return self.hostOsPath(os.getcwd())


  def makeProject(self, projName, targets, allProjects):
    """ Creates a project directory for the named Targets file (projName)
        and its list of Java targets (targets) """

    outProjName = projName.replace(os.sep, ".")
    outDir = self.workspacePath + outProjName

    projFile = outDir + os.sep + ".project"
    classpathFile = outDir + os.sep + ".classpath"
    if os.path.exists(projFile):
      print "Skipping existing project:", outProjName
      return

    print "Creating project", outProjName

    # TODO: Handle project/target.eclipseHook()  ?

    # figure out the dependencies for this project
    sources = []
    classpaths = []
    deps = []
    for target in targets:

      # add their source directories
      mySources = getattr(target, "sources", None)
      if mySources == None:
        mySources = []

      # and any required libraries
      myClasspaths = target.getClassPathElements()
      if myClasspaths == None:
        myClasspaths = []

      # Any genfiles outputs need to be in the sources.
      myIntermediatePaths = []
      if hasattr(target, "intermediatePaths"):
        myIntermediatePaths = target.intermediatePaths()

      # and references to any other java projects we can find
      myDeps = getattr(target, "required_targets", None)
      if myDeps == None:
        myDeps = []
      sources.extend(mySources)
      sources.extend(myIntermediatePaths)
      classpaths.extend(myClasspaths)
      deps.extend(myDeps)

    def removeDups(lst):
      """ de-duplicate list, ignoring order. """
      dict = {}
      for elem in lst:
        dict[elem] = ()
      return dict.keys()

    def removeSubtarget(target):
      """ turn real/proj/path:target into real/proj/path """
      idx = target.find(":")
      if idx > -1:
        return target[0:idx]
      else:
        return target

    def selfReferencesFilter(target):
      """ return true if this doesn't reference itself """
      return target != projName and len(target) > 0

    def followSymlinks(target):
      return paths.getRelativeBuildFilePath(target)

    def foreignProjectsFilter(target):
      """ return true if this references another eclipse-generating
          project """
      try:
        allProjects[target]
        return True
      except KeyError:
        return False # not found

    def propertyReconciler(pathelem):
      """ reconcile ant properties in classpath elements """
      return self.properties.resolveProperties(pathelem)

    def makeAbsolute(pathelem):
      """ make a path absolute """
      return os.path.abspath(pathelem)

    sources = removeDups(sources)
    sources = map(propertyReconciler, sources)

    classpaths = map(propertyReconciler, classpaths)

    newClasspaths = []
    for classpath in classpaths:
      splitPaths = classpath.split(":")
      newClasspaths.extend(splitPaths)
    classpaths = newClasspaths

    classpaths = removeDups(classpaths)
    classpaths = map(makeAbsolute, classpaths)

    deps = map(removeSubtarget, deps)
    deps = filter(selfReferencesFilter, deps)
    deps = map(followSymlinks, deps)
    deps = filter(foreignProjectsFilter, deps)
    deps = removeDups(deps)

    # start writing the outputs

    self.dirutils.mkdirRecursive(outDir)
    projFileHandle = open(projFile, "w")
    try:
      # write the .project file
      projFileHandle.write("""<?xml version="1.0" encoding="UTF-8"?>
<projectDescription>
  <name>""" + outProjName + """</name>
  <comment></comment>
  <projects></projects>
  <buildSpec>
    <buildCommand>
      <name>org.eclipse.ui.externaltools.ExternalToolBuilder</name>
      <triggers>full,incremental,</triggers>
      <arguments>
        <dictionary>
          <key>LaunchConfigHandle</key>
<value>&lt;project&gt;/.externalToolBuilders/ClouderaAntBuild.launch</value>
        </dictionary>
      </arguments>
    </buildCommand>
  </buildSpec>
  <natures>
    <nature>org.eclipse.jdt.core.javanature</nature>
  </natures>
  <linkedResources>""")

      for src in sources:
        projFileHandle.write("""
    <link>
      <name>""" + src + """</name>
      <type>2</type>
      <location>""" + self.fullPath(projName, src) + """</location>
    </link>""")

      projFileHandle.write("""
  </linkedResources>
</projectDescription>""")
    finally:
      projFileHandle.close()

    classFileHandle = open(classpathFile, "w")
    try:
      # write the .classpath file
      classFileHandle.write("""<?xml version="1.0" encoding="UFT-8"?>
<classpath>
  <classpathentry kind="con" path="org.eclipse.jdt.launching.JRE_CONTAINER"/>
  <classpathentry kind="output" path="output-bin" />
""")
      for src in sources:
        classFileHandle.write( \
            "  <classpathentry kind=\"src\" path=\"" + src + "\" />\n")
      for path in classpaths:
        classFileHandle.write( \
            "  <classpathentry kind=\"lib\" path=\"" \
            + self.hostOsPath(path) + "\" />\n")
      for dep in deps:
        depProjName = "/" + dep.replace(os.sep, ".")
        classFileHandle.write( \
            "  <classpathentry combineaccessrules=\"false\" kind=\"src\"" \
            +  "    path=\"" + depProjName + "\" />\n")

      classFileHandle.write("</classpath>\n")

    finally:
      classFileHandle.close()

    # Write the builder file.
    # first, figure out the list of targets to build for this project
    buildTargets = []
    for target in targets:
      if hasattr(target, "buildAntRules"):
        buildTargets.extend(target.buildAntRules())

    buildstr = ""
    for buildTarget in buildTargets:
      buildstr = buildstr + " " + buildTarget

    self.dirutils.mkdirRecursive(outDir + os.sep + ".externalToolBuilders")
    builderFileHandle  = open(outDir + os.sep + ".externalToolBuilders" \
        + os.sep + "ClouderaAntBuild.launch", "w")

    try:
      builderFileHandle.write( \
"""<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
<launchConfiguration
 type="org.eclipse.ui.externaltools.ProgramBuilderLaunchConfigurationType">
<booleanAttribute key="org.eclipse.debug.core.appendEnvironmentVariables"
  value="true" />
<booleanAttribute key="org.eclipse.debug.ui.ATTR_LAUNCH_IN_BACKGROUND"
  value="false" />
<stringAttribute key="org.eclipse.ui.externaltools.ATTR_LOCATION"
  value="/usr/bin/python" />
<stringAttribute key="org.eclipse.ui.externaltools.ATTR_RUN_BUILD_KINDS"
  value="full,incremental," />
<stringAttribute key="org.eclipse.ui.externaltools.ATTR_TOOL_ARGUMENTS"
  value="./build""" + buildstr + """\" />
<booleanAttribute key="org.eclipse.ui.externaltools.ATTR_TRIGGERS_CONFIGURED"
  value="true" />
<stringAttribute key="org.eclipse.ui.externaltools.ATTR_WORKING_DIRECTORY"
  value=\"""" + self.getBuildRoot() + """\" />
</launchConfiguration>
""")
    finally:
      builderFileHandle.close()


