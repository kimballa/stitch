# (c) Copyright 2009 Cloudera, Inc
#
# module: metamake.targets.stepwise
#
# Defines the StepBasedTarget class; follows a set of "steps" to direct the
# compilation of this target in an explicit fashion.

from collections import defaultdict
import os

import metamake.paths as paths
import metamake.steps.step as step
from   metamake.targets.anttarget import AntTarget
from   metamake.targets.target import Target
from   metamake.targets.targeterror import TargetError

class StepBasedTarget(AntTarget):
  def __init__(self, steps, version=None, manifest_file=None, required_targets=None, \
      clean_first=False, outputs=None):
    AntTarget.__init__(self)
    self.steps = steps
    self.version = version
    self.manifest_file = manifest_file
    self.user_outputs = outputs
    self.create_tarball = False
    self.clean_first = clean_first

    # calculate add'l dependencies from the steps list
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

    self.registered_zip_step = None
    self.registered_version = None
    self.resolved_input_files = []
    self.resolved_input_dirs = []
    self.force_build = False

    # Registration phase.
    for step in steps:
      step.register(self)


  def resolved_forced_build(self):
    """ Some step's inputs cannot be measured. We force a build. """
    self.force_build = True

  def resolved_input_file(self, filename):
    """ Some step requires a file (either source, or another target's output). Collect
        its name for uptodate checking.
    """
    self.resolved_input_files.append(filename)

  def resolved_input_dir(self, dirname):
    """ Some step requires a dir (either source, or another target's output). Collect
        its name for uptodate checking.
    """
    self.resolved_input_dirs.append(dirname)

  def register_output_zip(self, zip_step):
    """ A Tar is providing our zip; here's where it tells us where it goes. """
    self.registered_zip_step = zip_step


  def register_version_string(self, verstring):
    """ A Step is providing a version string that overrides the VerStringTarget
        reference, if any.
    """
    self.registered_version = verstring


  def generates_preamble(self):
    return True


  def get_package_name(self):
    return self.getSafeName()


  def get_assembly_top_dir(self):
    """ Returns the top-level directory for the package. The assembly dir
        (packagename-version/) is a subdir of this one. """

    basePath = "${outdir}/" + self.getBuildDirectory()
    if not basePath.endswith(os.sep):
      basePath = basePath + os.sep
    return basePath


  def getVerString(self):
    """ return the 'version' component of the assembly name, if it exists"""
    if self.registered_version != None:
      return self.registered_version
    elif self.version == None:
      return ""
    else:
      targetObj = self.getTargetByName(self.version)
      if targetObj == None:
        self.missingTarget(self.version)
      return targetObj.get_version()

  def getVerWithDash(self):
    """ return "-version" or "" if version is blank """
    shortVer = self.getVerString()
    if len(shortVer) > 0:
      return "-" + shortVer
    else:
      return ""

  def get_assembly_dir(self):
    return self.get_assembly_top_dir()


  def getPackageZip(self):
    """ Return the filename to the package .tar.gz artifact """

    if self.registered_zip_step is not None:
      return os.path.join(self.get_assembly_top_dir(), \
          self.registered_zip_step.get_tar_filename(self))
    else:
      return None


  def getStampPath(self):
    """
    Return the filename of a stamp file artifact, used for uptodate checks
    when no tarball is created.
    """
    return os.path.join(self.get_assembly_top_dir(), self.getSafeName() + ".stamp")


  def get_ant_rule_map(self):
    return {
      "build"   : self.getSafeName() + "-build",
      "clean"   : self.getSafeName() + "-clean",
      "default" : self.getSafeName() + "-build"
    }


  def packageRule(self, rule):
    """ emit the ant rule to create the package """

    (mainName, ruleType) = self.splitRuleName(rule)

    depAntRules = self.getAntDependencies(ruleType, [ "release-version" ])

    # input/output resolution
    for step in self.steps:
      step.resolve(self)

    text = ""

    if not self.force_build:
      # Figure out everything that we depend on. If it hasn't changed, then
      # don't build this. We measure the timestamps of all direct inputs vs.
      # our tarball output.
      # We exclude any inputs that are actually other files within our own build dir.
      uptodate_prop = self.getSafeName() + "-is-uptodate"
      text = text + "<target name=\"" + rule + "-uptodate\"\n"
      text = text + depAntRules + ">\n"
      text = text + "  <uptodate property=\"" + uptodate_prop + "\">\n"

      # Ant's uptodate task is somewhat stupid and can't deal with absolute paths
      # inside the srcfiles elements. Therefore we have to split up the input
      # paths by their leading directory component
      include_paths = (self.resolved_input_files +
                       [os.path.join(name, "**") for name in self.resolved_input_dirs])

      # We dont want to include anything inside the package path directory
      package_path = os.path.realpath(self.get_assembly_dir())

      grouped_paths = defaultdict(lambda: [])
      for path in include_paths:
        real_path = os.path.realpath(path)

        # Don't include things inside the package path
        if os.path.commonprefix([package_path, real_path]) == package_path:
          continue
        (dir, filename) = os.path.split(path)
        grouped_paths[dir].append(filename)

      for dir, filenames in grouped_paths.iteritems():
        text += "    <srcfiles dir=\"%s\">\n" % dir
        for filename in filenames:
          text += "        <include name=\"%s\" />\n" % filename
        text += "    </srcfiles>\n"

      if self.create_tarball:
        text = text + "    <mapper type=\"merge\" to=\"" + self.getPackageZip() + "\" />\n"
      else:
        text = text + "    <mapper type=\"merge\" to=\"" + self.getStampPath() + "\" />\n"

      text = text + "  </uptodate>\n"
      text = text + "  <echo message=\"" + self.getCanonicalName() + " uptodate: ${" \
          + uptodate_prop + "}\"/>\n"
      text = text + "</target>\n"

      text = text + "<target name=\"" + rule + "\" depends=\"" \
        + self.getSafeName() + "-build-uptodate\" unless=\"" + uptodate_prop + "\">\n"
    else:
      # build is forced.
      text = text + "<target name=\"" + rule + "\" "
      text = text + depAntRules + ">\n"

    if self.clean_first:
      text += "  <delete dir=\"" + self.get_assembly_dir() + "\"/>\n"

    # The actual package target work
    text = text + "  <mkdir dir=\"" + self.get_assembly_dir() + "\"/>\n"

    # Bring in all the steps
    for step in self.steps:
      text = text + step.emitPackageOps(self)

    if self.manifest_file != None:
      # check that our file list here equals the one we expect.
      # Give checkmanifest the --release flag if we're in release mode
      text = text + """
  <exec executable="${checkmanifest-exec}" failonerror="true">
    <arg value="%(manifest)s" />
    <arg value="%(pkgpath)s" />
    <arg value="--${version-subdir}" />
  </exec>
""" % {
      "manifest" : os.path.join("${basedir}", self.getInputDirectory(), \
          self.manifest_file),
      "pkgpath"  : self.get_assembly_dir()
    }

    if self.registered_zip_step == None and self.create_tarball:
      text = text + self.emit_tarball_text()
    elif not self.create_tarball:
      text = text + """
    <touch file="%s" />
    """ % self.getStampPath()

    text = text + "</target>\n"
    return text


  def emit_tarball_text(self):
    """ By default, we don't create a tarball of a StepBasedTarget. But PackageTarget
        (and others) may override this fact, zipping themselves up. """
    # This would only be called if self.create_tarball is true; this should only be
    # the case if someone else overrides our behavior.
    raise TargetError(self, "StepBasedTarget cannot create a tarball internally.")

  def cleanRule(self, rule):
    (mainName, ruleType) = self.splitRuleName(rule)
    text = """<target name="%(rule)s">
  <delete dir="%(basepath)s"/>
</target>
""" % { "rule"     : rule,
        "basepath" : self.get_assembly_top_dir() }

    return text


  def antRule(self, rule):

    if rule == "preamble":
      return self.output_target_preamble()

    (mainName, ruleType) = self.splitRuleName(rule)
    if ruleType == "build":
      return self.packageRule(rule)
    elif ruleType == "clean":
      return self.cleanRule(rule)


  def outputPaths(self):
    """ Return the list of user-controlled output paths. The list provided
        by the user will be files/dirs relative to the package base path;
        we absolutize them here before returning.
    """

    if self.user_outputs != None:
      absolute_outs = []
      for item in self.user_outputs:
        absolute_outs.append(self.normalize_user_path(item, is_dest_path=True))
      return absolute_outs
    else:
      return []
