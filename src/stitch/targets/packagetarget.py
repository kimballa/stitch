# (c) Copyright 2009 Cloudera, Inc
#
# module: stitch.targets.packagetarget
#
# Defines the PackageTarget class; creates a software distribution package
# composed of several other types of packages and targets. All of these are
# referred to as "steps." Derives from StepBasedTarget.

from collections import defaultdict
import os

import stitch.paths as paths
import stitch.steps.step as step
from   stitch.targets.anttarget import AntTarget
from   stitch.targets.stepwise import StepBasedTarget
from   stitch.targets.target import Target
from   stitch.targets.targeterror import TargetError

class PackageTarget(StepBasedTarget):
  def __init__(self, package_name, steps, version=None, \
      manifest_file=None, required_targets=None, create_tarball=True,
      clean_first=False, outputs=None):

    self.package_name = package_name

    StepBasedTarget.__init__(self, steps, version, manifest_file, \
        required_targets, clean_first, outputs)

    self.create_tarball = create_tarball


  def get_package_name(self):
    return self.package_name

  def get_assembly_top_dir(self):
    """ Returns the top-level directory for the package. The assembly dir
        (packagename-version/) is a subdir of this one. """

    basePath = "${redist-outdir}/" + self.getBuildDirectory()
    if not basePath.endswith(os.sep):
      basePath = basePath + os.sep
    return basePath


  def get_assembly_dir(self):
    """ Returns the assembly directory for this package; this sits underneath
       the assembly top dir.
    """
    pkgPath = os.path.join(self.get_assembly_top_dir(), \
        self.package_name + self.getVerWithDash() + os.sep)
    if not pkgPath.endswith(os.sep):
      pkgPath = pkgPath + os.sep
    return pkgPath


  def getPackageZip(self):
    """ Return the filename to the package .tar.gz artifact """

    if self.registered_zip_step is not None:
      return os.path.join(self.get_assembly_top_dir(), \
          self.registered_zip_step.get_tar_filename(self))
    else:
      return os.path.join(self.get_assembly_top_dir(), \
          self.package_name + self.getVerWithDash() + ".tar.gz")


  def getStampPath(self):
    """
    Return the filename of a stamp file artifact, used for uptodate checks
    when hen no tarball is created.
    """
    return os.path.join(self.get_assembly_top_dir(),
                        self.package_name + self.getVerWithDash() + ".stamp")


  def emit_tarball_text(self):
    # No Tar is zipping this up; we need to do it ourselves.
    pkgName = self.package_name + self.getVerWithDash()
    basePath = self.get_assembly_top_dir()
    tarFileName = os.path.join(basePath, pkgName + ".tar.gz")

    return """
  <exec executable="tar" failonerror="true">
    <arg value="czf" />
    <arg value="%(tarfilename)s" />
    <arg value="-C" />
    <arg value="%(pkgbasepath)s" />
    <arg value="%(pkgname)s" />
  </exec>
""" % {
      "tarfilename" : tarFileName,
      "pkgbasepath" : basePath,
      "pkgname"     : pkgName
    }


