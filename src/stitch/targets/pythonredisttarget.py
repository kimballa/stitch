# (c) Copyright 2009 Cloudera, Inc.
#
# pythonredisttarget.py
# defines the PythonRedistTarget object.

import os

import stitch.targets.anttarget as anttarget
import stitch.targets.packagetarget as packagetarget
import stitch.targets.pythontarget as pythontarget
from   stitch.targets.targeterror import TargetError
import stitch.targets.vertarget as vertarget
import stitch.steps.step as step

class AddDistUtilsDataFile(step.Step):
  """
    Marks a single file in a PythonRedistTarget's assembly dir
    as a data_file in the distutils setup.py file, and provides
    information as to where it should be installed.

    "filename" should refer to a file already under the package
    assembly directory, put there by CopyFile, CopyDir, etc.
  """

  def __init__(self, filename, install_dir):
    self.filename = filename
    self.install_dir = install_dir

  def emitPackageOps(self, package):
    # no-op; PythonRedistTarget will introspect into this obj and pull
    # out the filename and install_dir fields; we don't have to do anything
    # special during the packaging steps.
    return ""


class AddDistUtilsDataDir(step.Step):
  """
     Recursively marks all files in a subdir of a PythonRedistTarget's
     assembly dir as data_files in the distutils setup.py file, and
     provides info as to where they should be installed.

     "dirname" should refer to a dir already under the package assembly
     dir; e.g., put there by CopyDir.
  """

  def __init__(self, dirname, install_dir):
    self.dirname = dirname
    self.install_dir = install_dir


  def emitPackageOps(self, package):
    # no-op; PythonRedistTarget will introspect into this obj and pull
    # out the dirname and install_dir fields; we don't have to do anything
    # special during the packaging steps.
    return ""


class PythonRedistTarget(pythontarget.PythonBaseTarget):
  """ Copies a subset of the python sources into a single directory
      and tars it up; this enables you to create a redistributable version
      of a single python program (with the sources for all its dependencies
      included) without redistributing the entire bin/python/ tree.

      This is a packaging rule.

      Parameters:

      package_name     Req - Name to assign to the redistributed package
                            e.g., "MyProgram" (will make MyProgram.tar.gz
                            which expands to a MyProgram/ folder)
      steps      Opt - List of additional packaging steps to bundle in.
      version         Opt - Identifies a VerStringTarget detailing the
                            version of this package.

      data_paths       Opt - paths in the source tree containing data which need to
                            be present in the output dir

      required_targets Opt - Should be a list containing the python
                            targets you want to bundle into the
                            redistributable.

      use_dist_utils    Opt - Boolean (Default False); if True, generate a
                            distutils-compatible setup.py file and bundle
                            tarball accordingly.

      output_source_root Opt - By default, distutils setup.py generation will assume
                             that the root package for the python files is the
                             package base directory. If instead there is an
                             alternate "root" source package (e.g., "src/"),
                             list it here.
  """

  def __init__(self, package_name, steps=None, version=None, data_paths=None,
      required_targets=None, use_dist_utils=False, output_source_root=None):

    pythontarget.PythonBaseTarget.__init__(self)
    self.package_name = package_name
    if steps == None:
      self.steps = []
    else:
      self.steps = steps
    self.version = version
    self.data_paths = data_paths
    self.use_dist_utils = use_dist_utils
    self.output_source_root = output_source_root

    # get all dependency information (including dependencies from steps)
    allDeps = []

    if required_targets != None:
      allDeps.extend(required_targets)

    for step in self.steps:
      allDeps.extend(step.getDependencies())

    if version != None:
      allDeps.append(version)

    if len(allDeps) == 0:
      self.required_targets = None
    else:
      self.required_targets = allDeps


  def generates_preamble(self):
    return False

  def getPackageZip(self):
    """ return the filename of the redistName.tar.gz """

    return os.path.join("${redist-outdir}/" + self.getBuildDirectory(), \
        self.package_name + self.getVerWithDash() + ".tar.gz")


  def getVerString(self):
    """ return the 'version' component of the assembly name, if it exists"""

    # NOTE(aaron): This is very similar to PackageTarget.getVerString(), except
    # in the 'None' case.
    if self.version == None:
      # If you don't supply a version number to distutils, it forces 0.0.0
      return "0.0.0"
    else:
      return self.getTargetByName(self.version).get_version()


  def getVerWithDash(self):
    """ return "-version" or "" if version is blank """
    # TODO(aaron): This is a code clone from PackageTarget. merge.
    shortVer = self.getVerString()
    if len(shortVer) > 0:
      return "-" + shortVer
    else:
      return ""


  def get_assembly_top_dir(self):
    """ Returns the top-level directory for the package. The assembly dir
        (packagename-version/) is a subdir of this one. """

    basePath = "${redist-outdir}/" + self.getBuildDirectory()
    if not basePath.endswith(os.sep):
      basePath = basePath + os.sep
    return basePath


  def get_assembly_dir(self):
    """ return the dir where we copied hadoop to and built it in. Ensure
        that this ends with a '/' so PackageTargets can use it"""

    pkgPath = os.path.join("${redist-outdir}/" + self.getBuildDirectory(), \
        self.package_name + self.getVerWithDash() + os.sep)
    if not pkgPath.endswith(os.sep):
      pkgPath = pkgPath + os.sep
    return pkgPath


  def get_ant_rule_map(self):
    return {
      "build"   : self.getSafeName() + "-build",
      "clean"   : self.getSafeName() + "-clean",
      "default" : self.getSafeName() + "-build",
      "doc"     : self.getSafeName() + "-doc",
    }


  def cleanRule(self, rule):

    text = "<target name=\"" + rule + "\">\n"
    dest_dir = "${redist-outdir}/" + self.getBuildDirectory()
    text = text + "  <delete dir=\"" + dest_dir + "\" />\n"
    text = text + "</target>\n"
    return text


  def create_echo_statement(self, file_path, contents):
    """
    Creates an echo statement for write_dist_utils_data_files_echos.
    """
    return """<echo file="%(file_path)s" append="true">%(contents)s
</echo>
""" % locals()

  def write_dist_utils_data_files_echos(self, file_path):
    """
    Loops through all components, picks out those that match the signatures
    of AddDistUtilsDataFile and AddDistUtilsDataDir, and returns ant
    echo statements that append file_path.  The echo statements will
    look like:

    <echo file="%(datafiles)s" append="true">srcFile\tdestDir
    </echo>
    <echo file="%(datafiles)s" append="true">srcFile2\tdestDir2
    </echo>
    """
    ret = []
    for c in self.steps:
      if hasattr(c, "install_dir") and hasattr(c, "filename"):
        assert not c.filename.__contains__("\t")
        assert not c.install_dir.__contains__("\t")
        ret.append(self.create_echo_statement(file_path, "%s\t%s" \
            % (self.normalize_user_path(c.filename, is_dest_path=True, include_basedir=False), \
            c.install_dir)))
      elif hasattr(c, "install_dir") and hasattr(c, "dirname"):
        assert not c.dirname.__contains__("\t")
        assert not c.install_dir.__contains__("\t")
        ret.append(self.create_echo_statement(file_path, "%s\t%s" \
            % (os.path.join(self.normalize_user_path(c.dirname, is_dest_path=True, \
            include_basedir=False), "**"),
            c.install_dir)))
    return '\n'.join(ret)


  def get_dist_utils_data_files_ant_path(self):
    """
    Returns a path where ant should write distutils data files to.

    The path is typically bin/path/to/project/distutils-datafiles.
    """
    return os.path.join(self.get_assembly_top_dir(), "distutils-datafiles")

  def packageRule(self, rule):
    (mainName, ruleType) = self.splitRuleName(rule)
    dest_dir = "${redist-outdir}/" + self.getBuildDirectory()
    copyTarget = dest_dir + os.sep + self.package_name + self.getVerWithDash()

    text = "<target name=\"" + rule + "\" " \
        + self.getAntDependencies("build", ["python-prereqs"]) + ">\n"
    text = text + "  <mkdir dir=\"" + copyTarget + "\" />\n"

    # TODO(aaron): make recursive copy-in process a step/action.
    # figure out everyone we transitively depend on
    dependTargets = self.getRecursiveDependencyTargetObjs()
    allowedLanguages = [ "python", "thrift", "none" ]
    for target in dependTargets:
      try:
        allowedLanguages.index(target.language())
      except ValueError:
        raise TargetError(self, "Cannot build PythonRedist " + self.getCanonicalName() \
            + " which transitively depends on target " + target.getCanonicalName() \
            + " in language: " + str(target.language()))

      try:
        sources = target.getSources()
        for src in sources:
          text = text + self.copySource(target.normalize_user_path(src), copyTarget)
      except AttributeError:
        # Doesn't have getSources(); maybe it generates intermediates
        try:
          sources = target.intermediatePathsForLang(self.language())
          for src in sources:
            text = text + self.copySource(src, copyTarget)
        except AttributeError:
          # Doesn't have that either. Just ignore.
          pass

      text = text + target.copyDataPaths(copyTarget)

    text = text + self.copyDataPaths(copyTarget)

    # Bring in steps with primary actions
    for step in self.steps:
      text = text + step.emitPackageOps(self)

    # TODO(aaron): Make distutils setup.py production a step/action.
    if self.use_dist_utils:
      if self.output_source_root != None and len(self.output_source_root) > 0:
        source_root = self.normalize_user_path(self.output_source_root)
      else:
        source_root = "."

      # Generate a setup.py file and wrap the tarball using distutils

      text = text + """
  <delete file="%(datafiles)s" quiet="true" failonerror="false" />
%(datafiles_echo)s
  <exec executable="${make-setup-exec}" failonerror="true" dir="%(targetdir)s">
    <arg value="--name" />
    <arg value="%(packagename)s" />
    <arg value="--verstring" />
    <arg value="%(verstring)s" />
    <arg value="--srcdir" />
    <arg value="%(source_root)s" />
    <arg value="--basedir" />
    <arg value="%(targetdir)s" />
    <arg value="--datafiles" />
    <arg value="%(datafiles)s" />
  </exec>
  <exec executable="${python-exec}" failonerror="true" dir="%(targetdir)s">
    <arg value="setup.py" />
    <arg value="sdist" />
  </exec>
  <move todir="%(basedir)s" file="%(targetdir)s/dist/%(packagename)s-%(verstring)s.tar.gz" />
  <delete dir="%(targetdir)s/dist" />
  <delete dir="%(targetdir)s/MANIFEST" />
""" % { "targetdir"      : copyTarget,
        "packagename"    : self.package_name,
        "verstring"      : self.getVerString(),
        "source_root"    : source_root,
        "basedir"        : self.get_assembly_top_dir(),
        "datafiles"      : self.get_dist_utils_data_files_ant_path(),
        "datafiles_echo" : self.write_dist_utils_data_files_echos(self.get_dist_utils_data_files_ant_path()),
      }
    else:
      # Create the release tarball ourselves
      tarFilename = self.getPackageZip()
      text = text + "  <exec executable=\"tar\">\n"
      text = text + "    <arg value=\"czf\" />\n"
      text = text + "    <arg value=\"" + tarFilename + "\" />\n"
      text = text + "    <arg value=\"-C\" />\n"
      text = text + "    <arg value=\"" + dest_dir + "\" />\n"
      text = text + "    <arg value=\"" + self.package_name + self.getVerWithDash() + "\" />\n"
      text = text + "  </exec>\n"

    text = text + "</target>\n"
    return text


  def epydoc_rule(self, rule):
    """ Generate epydoc rule """

    (mainName, ruleType) = self.splitRuleName(rule)

    if self.output_source_root == None:
      srcdir = self.get_assembly_dir()
    else:
      srcdir = os.path.join(self.get_assembly_dir(), self.output_source_root)

    outdir = "${docs-outdir}/" + self.getBuildDirectory()

    text = "<target name=\"" + rule + "\" depends=\"" + self.getSafeName() + "-build\">\n"

    src_args = []
    if self.required_targets != None:
      # For all the sources that we incorporate directly, put their module/package
      # names on the list to create documentation for.
      for req_name in self.required_targets:
        target = self.getTargetByName(req_name)
        try:
          src_list = target.getSources()
        except AttributeError:
          # Doesn't have getSources. Might be an intermediate generator.
          try:
            src_list = target.intermediatePathsForLang(self.language())
          except AttributeError:
            # Doesn't generate intermediates, either. Ignore.
            src_list = []

        for src_name in src_list:
          base_name = os.path.basename(src_name)
          if base_name == "":
            base_name = os.path.basename(os.path.dirname(src_name))
          elif not base_name.endswith(".py"):
            continue
          else:
            base_name = base_name.replace(".py","")
          src_args.append("    <arg value=\"" + base_name + "\" />\n")

    if len(src_args) > 0:
      text = text + "  <mkdir dir=\"" + outdir + "\"/>\n"
      text = text + "  <exec executable=\"${epydoc-exec}\" failonerror=\"true\">\n"
      text = text + "    <env key=\"PYTHONPATH\"\n"
      text = text + "      value=\"" + srcdir + ":$PYTHONPATH\" />\n"
      text = text + "    <arg value=\"--html\"/>\n"
      text = text + "    <arg value=\"-o\"/>\n"
      text = text + "    <arg value=\"" + outdir + "\"/>\n"
      text = text + "    <arg value=\"--parse-only\"/>\n"
      text = text + "    <arg value=\"--name\"/>\n"
      text = text + "    <arg value=\"" + self.package_name + "\"/>\n"
      text = text + "    <arg value=\"--fail-on-error\"/>\n"

      for arg in src_args:
        text = text + arg

      text = text + "  </exec>\n"
    text = text + "</target>\n"

    return text


  def antRule(self, rule):

    (mainName, ruleType) = self.splitRuleName(rule)

    if ruleType == "clean":
      return self.cleanRule(rule)
    elif ruleType == "build":
      return self.packageRule(rule)
    elif ruleType == "doc":
      return self.epydoc_rule(rule)
    else:
      raise TargetError(self, "Unsupported PythonRedist rule type: " + ruleType)


