# (c) Copyright 2009 Cloudera, Inc.
#
# stitch.targets.target
# defines the baes Target object, from which all subclasses derive.
# not to be instantiated directly. Also contains the lookup map from
# target name to object

import inspect
import itertools
import os
import re
import sys

import stitch.buildfile as buildfile
import stitch.paths as paths
from   stitch.targets.targeterror import TargetError


__anonCounter = 0
def getAnonymousName():
  """ returns a guaranteed-unique anonymous name
      for a target in case it is not assigned a
      proper canonicalized name. Note that this is
      not thread-safe. """
  global __anonCounter

  anonName = "_rule_" + str(__anonCounter)
  __anonCounter = __anonCounter + 1
  return anonName


targetMap = {}

def mapNameToTarget(target_name, targetObj):
  global targetMap
  targetMap[target_name] = targetObj


class Target(object):
  """ Base target class. Not intended to be directly
      constructed.

      Target objects are constructed by the Targets files
      loaded in from various directories.

      When referencing other targets, if you just need the
      default target from a Targets file, it is sufficient
      to provide the path name where the Targets file can
      be found. These files may define named objects which
      represent targets. e.g,

      myProgram = JavaTarget( .... )

      Assuming this is in path src/foo/Targets, other
      modules can simply depend on "src/foo".

      If there was a second target in the same Targets
      file:

      otherProgram = JavaTarget( ... )

      Then references to "src/foo:otherProgram" would
      select this target. The first target created in
      the file is the default target, unless overridden
      by calling defaultTarget(someTarget) which sets
      the default target for a project.

      Named targets in the current module can be specified
      by prefixing them with a colon e.g., ":otherProgram"
  """

  def __init__(self):
    # Save the original definition location of this target so we
    # can provide useful traces in TargetError
    self.definition_location = self._get_definition_location()

    self.canonicalName = getAnonymousName()
    self.safeName = self.canonicalName
    self.generated = False
    self.is_anon = True

    # upon construction, register with the build file.
    from stitch.buildfile import getCurBuildFile
    curBuildFile = getCurBuildFile()
    curBuildFile.addTarget(self)

    self.build_file = curBuildFile

  def _get_definition_location(self):
    """
    Return a tuple (filename, line) by searching up the current
    call stack to find the line in a targets file where this
    target was defined.
    """
    for i in itertools.count(1):
      try:
        frame = sys._getframe(i)
      except ValueError:
        # We reached the top of the stack and couldn't find a target file
        return None
      (filename,lineno,funcname,context,lineidx) = inspect.getframeinfo(frame)
      if os.path.basename(filename) == buildfile.DEFAULT_BUILD_FILENAME:
        return (filename, lineno)

  def __str__(self):
    if self.definition_location:
      def_loc = "%s:%d" % self.definition_location
    else:
      def_loc = "<unknown location>"
    return "<target %s defined at %s>" % (self.canonicalName, def_loc)

  def validate_arguments(self):
    """
    Ensure that arguments are reasonable types, etc.

    Subclasses should throw TargetErrors for validation issues, and be sure to
    call superclass validation.
    """
    pass

  def isGenerated(self):
    """ return True if we already created our output rules """
    return self.generated

  def markAsGenerated(self):
    self.generated = True

  def clearGenerated(self):
    self.generated = False

  def isStandalone(self):
    return False

  def isStandaloneExempt(self):
    return False

  def language(self):
    """ return the source langauge for this target """
    return None

  def is_anonymous(self):
    return self.is_anon

  def setCanonicalName(self, name, anon):
    """ sets the canonical name for this target """
    self.canonicalName = name
    self.is_anon = anon

    # register this canonical name for the target.
    mapNameToTarget(name, self)

  def getCanonicalName(self):
    return self.canonicalName

  def setSafeName(self, name):
    """ sets the ant-safe name for this target """
    self.safeName = name

  def getSafeName(self):
    return self.safeName


  def getBuildDirectory(self):
    """ get output build directory for the target. Must end with a '/'
        so that we can distinguish this from files in outputPaths().
        This returns the "relative" build directory which may exist
        under ${outdir}, ${redist-outdir}, etc. """
    outDir = self.getCanonicalName().replace(":", "_")
    if not outDir.endswith(os.sep):
      outDir = outDir + os.sep
    # Remove the initial '//' from the canonical name when
    # converting to a real path step.
    return paths.dequalify(outDir)


  def get_assembly_dir(self):
    """ The directory where compilation steps direct their outputs.
        This is the directory used by the "%(assemblydir)" and "$/"
        user macros.

        This returns an absolute path (albeit usually one parameterized by an
        ant macro).

        Whereas the getBuildDirectory() method returns a dir name which may
        occur under one of several build directory roots; this joins
        the appropriate root to the build dir.
        This should be overridden by subclasses.
    """
    return os.path.join("${outdir}", self.getBuildDirectory())


  def get_assembly_top_dir(self):
    """ An output directory used entirely by a single target which may
        or may not have the asesmbly dir as a subdirectory (it may also
        equal the assembly dir). This is used by the %(assemblytopdir)
        user macro.
    """
    return self.get_assembly_dir()


  def getInputDirectory(self):
    """ return the directory where this came from """
    canonical_name = self.getCanonicalName()
    targetIdx = canonical_name.find(":")
    if targetIdx > -1:
      input_dir = canonical_name[0:targetIdx]
    else:
      input_dir = canonical_name

    return paths.dequalify(input_dir)


  def substitute_macros(self, value):
    """ Substitute values in for macros in user strings.
        Recognizes the following macros:

        %(assemblydir)      The target's assembly directory
        %(assemblytopdir)   Targets intended for packaging may have a topdir
                            that is the parent of %(assemblydir). For other
                            targets, this may equal %(assemblydir).
        %(srcdir)           Directory containing the current Targets file
        %(basedir)          Base directory for the build tree

        It is an error to use a macro that is not defined for the
        current target type (e.g., assemblydir in a JarTarget).
    """

    if not hasattr(self, "assembly_re") or self.assembly_re == None:
      # None of the macros have been compiled yet. Do so now.
      self.assembly_re = re.compile("%\\(assemblydir\\)")
      self.topdir_re = re.compile("%\\(assemblytopdir\\)")
      self.src_re = re.compile("%\\(srcdir\\)")
      self.base_re = re.compile("%\\(basedir\\)")

      # This regex matches any %%(foo), and will be used to replace it with %(foo)
      # so that you can escape macros.
      self.escape_re = re.compile("%(%\\([^\\)]*\\))")

    def subst_re(r, input, replacement=""):
      """ each span matched by 'r' in 'input' is replaced by 'replacement',
          unless it is preceeded by another '%' (escape char)

          If the matcher returns any (groups), ignores 'replacement' and
          uses the first group
      """
      ESCAPE_CHAR = "%"
      offset = 0
      while offset < len(input):
        m = r.search(input, offset)
        if m == None:
          break # no more matches left.
        (start, end) = m.span()
        if start > 0 and input[start - 1] == ESCAPE_CHAR:
          # this is ecsaped; ignore it.
          offset = start + 1
          continue
        else:
          # do the replacement
          if len(m.groups()) > 0:
            repl = m.groups()[0]
          else:
            repl = replacement

          input = input[0:start] + repl + input[end:]
          offset = start + len(repl)

      return input

    # Expand real macros first.
    value = subst_re(self.assembly_re, value, self.get_assembly_dir())
    value = subst_re(self.topdir_re , value, self.get_assembly_top_dir())
    value = subst_re(self.src_re, value, os.path.join("${basedir}", self.getInputDirectory()))
    value = subst_re(self.base_re, value, "${basedir}")

    # Unescape macro-like strings.
    value = subst_re(self.escape_re, value)

    return value


  def normalize_select_user_path(self, path):
    """
        Operates like normalize_user_path() on "$/..." and "//..." strings.
        Does not call substitute_macros().
    """

    if path.startswith(paths.ROOT_QUALIFIER):
      # buildroot-relative
      return "${basedir}" + os.sep + paths.dequalify(path)
    elif path.startswith(paths.OUTDIR_QUALIFIER):
      # outdir-relative
      return os.path.join(self.get_assembly_dir(), paths.dequalify(path))
    else:
      return path


  def normalize_user_path(self, path, is_dest_path=False, include_basedir=True):
    """
        A path provided by the user (e.g., to source files) has one of the following
        forms:
           straight-relative (e.g., 'foo/bar')
              This may be relative to the cwd of the targets file for input/src paths,
              but is relative to the outdir for output/destination paths.
           buildroot-relative (e.g., '//foo/bar') -- relative to the build root
           outdir-relative (e.g., '$/foo/bar') -- relative to the target's outdir
           absolute (e.g., '/home/aaron/foo') -- absolute.
           java-property (e.g., '${somedir}')

        Return absolute and java-property paths as-is; turn any of the relative forms
        above into strings involving ${basedir} for use in the ant build.xml file.

        If is_dest_path is False, then make relative to cwd. Otherwise, relative to $/.

        if include_basedir is false, then the leading "${basedir}/" is omitted.

        Also calls substitute_macros() on the input path.
    """

    path = self.substitute_macros(path)

    if path.startswith(paths.ROOT_QUALIFIER):
      # buildroot-relative
      if include_basedir:
        return "${basedir}" + os.sep + paths.dequalify(path)
      else:
        return paths.dequalify(path)
    elif path.startswith(paths.OUTDIR_QUALIFIER):
      # outdir-relative
      return os.path.join(self.get_assembly_dir(), paths.dequalify(path))
    elif os.path.isabs(path) or path.startswith("${"):
      # absolute path or java property.
      return path
    else:
      if is_dest_path:
        # destination-relative
        relative_to_dir = self.get_assembly_dir()
      else:
        # local-relative
        relative_to_dir = self.getInputDirectory()

      if include_basedir:
        return os.path.join("${basedir}", relative_to_dir, path)
      else:
        return os.path.join(relative_to_dir, path)


  def getBuildFile(self):
    """ returns the BuildFile object which contains this Target"""
    return self.build_file

  def outputPaths(self):
    """ return a list of paths to output objects generated
        by this target. Directories *must* end with '/', files must
        not; this is so that IncludeOutput in PackageTarget can
        distinguish between the two cases. """
    return []

  def get_required_targets(self):
    return self.force(self.required_targets)

  def getClassPathElements(self):
    return []

  def generatesAntRules(self):
    """ return True if this generates output for build.xml
        as its primary build generator method """
    return False

  def isEmpty(self):
    """ return True if this Target should create no rules during
        default generation """
    return False

  def getTargetByName(self, target_name, allowMissingTargets=False):
    """ return a Target object by its (string-based) name.

        This method is called within the context of a referee Target,
        as target names may be relative to the current directory or targets
        file.
    """
    global targetMap
    from stitch.buildfile import SUBTARGET_SPECIFIER

    if target_name.startswith(SUBTARGET_SPECIFIER):
      # this is a file-local target. Use my own BuildFile's
      # canonical name.
      build_file = self.getBuildFile()
      target_name = build_file.getCanonicalName() + target_name
    else:
      # the path step of the target might involve symlinks
      # to get to the real target. normalize this.

      # first, split "some/path/part:subtarget"
      # into "some/path/part" and ":subtarget"
      subTargetPos = target_name.find(SUBTARGET_SPECIFIER)
      if subTargetPos == -1:
        subTargetPos = len(target_name)
      pathPart = target_name[0:subTargetPos]
      subTargetPart = target_name[subTargetPos:]

      # if pathPart starts with '//', then it's an absolute
      # path within the build tree. Otherwise, add our own
      # canonical path to the front end.
      if pathPart.startswith(paths.ROOT_QUALIFIER):
        # drop the leading root qualifier for reconciliation later
        pathPart = pathPart[len(paths.ROOT_QUALIFIER):]
      else:
        # this is relative to current directory.
        build_file = self.getBuildFile()
        my_path = build_file.getBuildFileDirectory()

        # join the buildfile's directory with the target path part,
        # then resolve any '..', etc.
        pathPart = os.path.normpath(os.path.join(my_path, pathPart))

      # now reconcile the build file path
      realifiedPathPart = paths.getRelativeBuildFilePath(pathPart)

      target_name = paths.ROOT_QUALIFIER + realifiedPathPart + subTargetPart

    # now that everything is in canonical form, look up the actual
    # Target object associated with this name.
    try:
      return targetMap[target_name]
    except KeyError:
      if allowMissingTargets:
        return None
      else:
        self.missingTarget(target_name)


  def missingTarget(self, target_name):
    """ Prints an error message and exits when a Target cannot be found """
    print "Error: Target " + self.getCanonicalName() + " in build file " \
        + self.getBuildFile().getFileName() + " referenced missing target: " + target_name
    sys.exit(1)

  def force(self, val):
    """ If a val may represent a thunk, then we force it before returning our results,
        according to the following rules:
          lists are processed iteratively
          thunks have their force() method called. 
          strings or anything else are returned as-is

        If a val is a list, and contains thunks, if those thunks return lists, they
        are all flattened into the output list. Thunks may not return more thunks,
        only final values (strings, or lists of strings).
    """

    if isinstance(val, list):
      out = []
      for v in val:
        this_out = self.force(v)
        if isinstance(this_out, list):
          # flatten lists
          out.extend(this_out)
        else:
          out.append(this_out)
      return out
    elif hasattr(val, 'force'):
      return val.force(self)
    else:
      return val
      
    
