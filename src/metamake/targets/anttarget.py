# (c) Copyright 2009 Cloudera, Inc.
#
# metamake.targets.anttarget
# defines the base "AntTarget" abstract class from which all ant-target-
# producing subclasses derive. Contains a lot of convenience methods for
# resolving dependencies in the ant targets.

import os

import metamake.paths as paths
from   metamake.targets.targeterror import TargetError
from   metamake.targets.target import Target

# constant values for the selection parameter to getDependencyClassPaths
AllDependencies = 0
StandaloneDepsOnly = 1
ExcludeStandaloneChildren = 2
ExcludeStandaloneDeps = 3

class AntTarget(Target):
  """ Abstract class that provides functions that most
      targets generating ant rules will use. Subclassing AntTarget
      is not required for generating ant rules; as long
      as generatesAntRules() returns true, the ant generator
      will work. But this provides a common base that you are
      recommended to use. """

  def __init__(self):
    Target.__init__(self)
    self.classpath_elements = []
    self.data_paths = None
    if not hasattr(self, "required_targets"):
      self.required_targets = None

  def validate_arguments(self):
    """ Ensure that arguments are reasonable types, etc. """
    Target.validate_arguments(self)
    if self.required_targets != None and not isinstance(self.required_targets, list):
      raise TargetError(self, "required_targets must be a list")

  def generatesAntRules(self):
    return True

  def get_ant_rule_map(self):
    """ Returns a map from phase name |--> antrule name
        for all rules this Target generates.

        The special phase name "default" defines the default rule for the target.

        e.g.:
           { "build"   : "my-target-build",
             "clean"   : "my-target-clean"
             "default" : "my-target-build"
           }
    """

  def testShellAntRules(self):
    """ return name of test rule """
    return []

  def generates_preamble(self):
    """ Returns True if this Target generates additional code that
        needs to go in the buildfile preamble. If true, then the
        antRule() method will be called with "preamble" as the rule type.
    """
    return False

  def intermediatePathsForLang(self, lang):
    """ return a list of paths containing intermediate source
        created by this target specific to a given language """
    return self.intermediatePaths()

  def intermediatePaths(self):
    """ return a list of paths that contain intermediate source
        genfiles created by this target """
    return []

  def antRule(self, rule):
    raise TargetError(self, "AntTarget is an abstract class")

  def getClassPathElements(self):
    """ all AntTarget subclasses have a classpath_elements field """
    if self.classpath_elements == None:
      return []
    return self.classpath_elements

  def getDependencyClassPaths(self, ruleType, recursive=False,
      filter=AllDependencies):
    return self.getDependencyClassPathsAux(ruleType, recursive, filter, [])

  def getDependencyClassPathsAux(self, ruleType, recursive, filter, seen):
    """ return the list of outputs generated by our dependencies
        for including in our classpath. If recursive is set
        to true, then also include all classpath elements
        required by those targets, as well as any targets
        they depend on and so forth. The 'seen' list is used
        by the recursive finder; do not manipulate it directly.

        If filter is AllDependencies, grab everything.
                  StandaloneDepsOnly, then stop if we hit a jar that has
                                      standalone_exempt = True (we are trying
                                      to find jars that should be packed into
                                      lib/ in the jar)
           ExcludeStandaloneChildren, then grab all jars initially, but set
                                      our sense to ExcludeStandaloneDeps if
                                      we find a standaloneJar (we are trying
                                      to find things that need to go in an
                                      exec target's lib/ dir)
               ExcludeStandaloneDeps, then stop if we hit a jar with
                                      standalone_exempt = False


    """

    classPaths = []
    if ruleType == "build" or ruleType == "test":
      # for any ant-based deps, depend on their -build outputs
      if self.required_targets != None:
        for target_name in self.required_targets:
          target = self.getTargetByName(target_name)
          if None == target:
            raise TargetError(self, "Could not find dependency: " + target_name)
          elif target.generatesAntRules():
            try:
              seen.index(target)
            except ValueError:
              # haven't seen this target before. recurse on it.
              seen.append(target)
              include = (filter == AllDependencies \
                  or filter == ExcludeStandaloneChildren \
                  or (filter == StandaloneDepsOnly and not
                      target.isStandaloneExempt()) \
                  or (filter == ExcludeStandaloneDeps and
                      target.isStandaloneExempt()))
              if include:
                classPaths.append(target.getSafeName() + ".outputs")
                if recursive:
                  # grab their straight-up classpath elements too
                  classPaths.append(target.getSafeName() + ".classpath")
                  if hasattr(target, "getDependencyClassPaths"):
                    if target.isStandalone() \
                        and filter == ExcludeStandaloneChildren:
                      nextFilter = ExcludeStandaloneDeps
                    else:
                      nextFilter = filter
                    classPaths.extend( \
                        target.getDependencyClassPathsAux(ruleType, True,
                        nextFilter, seen))

    return classPaths

  def getRecursiveDependencyTargetObjs(self):
    """ return a list containing the complete set of Target objects we
        depend on recursively. """


    def dfsTargetFinder(targetObj, deps):
      newTargets = []
      if targetObj.required_targets != None:
        for target_name in targetObj.required_targets:
          target = targetObj.getTargetByName(target_name)
          if None == target:
            raise TargetError(self, "Could not find dependency " + target_name \
                + " from " + self.getCanonicalName())
          elif target.generatesAntRules():
            try:
              deps.index(target)
            except ValueError:
              # haven't seen this target before.
              deps.append(target)
              newTargets.append(target)
      for newTarget in newTargets:
        dfsTargetFinder(newTarget, deps)

    deps = []
    dfsTargetFinder(self, deps)

    return deps



  def getAntDependencies(self, ruleType, extraDependencies=[]):
    """ return the dependencies we have on other targets
        based on the rule type we're generating (build, etc.).
        ruleType can actually be a comma,delimited,list
        of real rule types"""
    deps = []
    deps.extend(extraDependencies)

    allRuleTypes = ruleType.split(",")

    def containsAny(haystack, needles):
      """ return true if the haystack list contains at least one element of
          the needles list """
      for needle in needles:
        try:
          haystack.index(needle)
          return True
        except ValueError:
          pass # didn't find this one

      return False


    # production rules depend on the top-level init rule.
    if containsAny(allRuleTypes, ["build", "test"]):
      deps.append("init")

    if containsAny(allRuleTypes, ["build"]):
      # for any ant-based deps, depend on their -build
      if self.required_targets != None:
        for target_name in self.required_targets:
          target = self.getTargetByName(target_name)
          if None == target:
            raise TargetError(self, "Could not find dependency: " + target_name)
          elif target.generatesAntRules():
            target_map = target.get_ant_rule_map();
            try:
              deps.append(target_map["build"])
            except KeyError:
              pass
          else:
            print "Warning: ant target " + self.getCanonicalName() \
                + " depends on non-ant target: " + target_name

    if len(deps) == 0:
      return ""
    else:
      text = "depends=\""
      first = True
      for dep in deps:
        if not first:
          text = text + ","
        first = False
        text = text + dep
      text = text + "\""
      return text


  def getDependencySources(self):
    """ return a list of intermediate dirs to include as 'src'
        entries when compiling. These are genfiles outputs from
        other targets. """
    deps = []
    if self.required_targets != None:
      for target_name in self.required_targets:
        target = self.getTargetByName(target_name)
        if None == target:
          raise TargetError(self, "Could not find dependency: " + target_name)
        elif target.generatesAntRules():
          deps.extend(target.intermediatePaths())

    return deps

  def getDependencySourcesForLang(self, lang):
    """ return a list of intermediate dirs to include as 'src'
        entries when compiling. These are genfiles outputs from
        other targets. This should be used to retrieve only the
        dependency sources approporiate to a particular language."""

    deps = []
    if self.required_targets != None:
      for target_name in self.required_targets:
        target = self.getTargetByName(target_name)
        if None == target:
          raise TargetError(self, "Could not find dependency: " + target_name)
        elif target.generatesAntRules():
          deps.extend(target.intermediatePathsForLang(lang))

    return deps


  def splitRuleName(self, rule):
    """ split the rule name into two parts, representing the name
        of the input target and the type of rule being produced.
        Return (mainNamePart, ruleTypePart) """

    # split the rule of form "foo-build" into "foo" and "build"
    dashIndex = rule.rfind("-")
    if dashIndex > -1:
      mainName = rule[0:dashIndex]
      ruleType = rule[dashIndex + 1:]
    else:
      raise TargetError(self, "Ant Target generated weird rule " + rule)
    return (mainName, ruleType)


  def output_target_preamble(self):
    """ Basic preamble that ant targets involving outputs and/or classpaths
        should use to define their named path entities.
    """
    return self.emit_output_pathref() + self.emit_classpath_pathref()


  def emit_classpath_pathref(self):
    """ Emits a named <path> .. </path> structure to encapsulate the classpath
        of this target. Used by recursive classpath references elsewhere in
        the compilation process.

        This should be called as part of the target's preamble.
    """

    elems = self.getClassPathElements()
    text = "<path id=\"" + self.getSafeName() + ".classpath\">\n"
    for elem in elems:
      text = text + "  <pathelement path=\"" + elem + "\"/>\n"
    text = text + "</path>\n"
    return text


  def emit_output_pathref(self):
    """ Emits a named <path> .. </path> structure to encapsulate the outputs
        of this target. Used by recursive classpath references elsewhere in
        the compilation process.

        This should be called as part of the target's preamble.
    """
    elems = self.outputPaths()
    text = "<path id=\"" + self.getSafeName() + ".outputs\">\n"
    for elem in elems:
      if elem.endswith(os.sep):
        text = text + "  <fileset dir=\"" + elem + "\">\n"
        text = text + "    <include name=\"**\" />\n"
        text = text + "  </fileset>\n"
      else:
        text = text + "  <pathelement path=\"" + elem + "\"/>\n"
    text = text + "</path>\n"
    return text


  def copyDataPaths(self, dest_dir):
    """ Called during build procedures to copy data paths to the output
        directory. This is a standard component of build rules """

    text = ""

    if self.data_paths != None:
      for data_path in self.data_paths:
        full_data_path = self.normalize_user_path(data_path)
        text = text + "  <exec executable=\"rsync\">\n"
        text = text + "    <arg value=\"-r\" />\n"
        text = text + "    <arg value=\"--copy-links\" />\n"
        text = text + "    <arg value=\"--perms\" />\n"
        text = text + "    <arg value=\"--times\" />\n"
        text = text + "    <arg value=\"--update\" />\n"
        text = text + "    <arg value=\"" + full_data_path + "\" />\n"
        text = text + "    <arg value=\"" + dest_dir + "\" />\n"
        text = text + "  </exec>\n"

    return text

