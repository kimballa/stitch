# (c) Copyright 2009 Cloudera, Inc.
#
# module: outputsteps
# contains Step classes which incorporate the output of one
# target into the build process of another.

import os

import stitch.paths as paths
import stitch.steps.step as step
from   stitch.targets.targeterror import TargetError

class IncludePackage(step.Step):
  """ Incorporate one 'package' target inside another.
      Inputs:
        target_name    -- The name of the target to 'package' and include
        include_zip    -- If true, incorporate the zip, not the assembly dir
        dest_dir       -- where the included artifacts go. default is right
                         in the assembly dir.
  """

  def __init__(self, target_name, include_zip=False, dest_dir=None):
    step.Step.__init__(self)
    self.target_name = target_name
    self.include_zip = include_zip
    self.dest_dir = dest_dir

  def getDependencies(self):
    return [ self.target_name ]


  def resolve(self, package):
    pkg_target = package.getTargetByName(self.target_name)
    if self.include_zip:
      if not hasattr(pkg_target, "getPackageZip"):
        raise TargetError(package, "Error: Target " + pkg_target.getCanonicalName() \
            + " does not generate a package tarball. (Did you want an IncludeOutput?)")
      zip_file = pkg_target.getPackageZip()
      if None == zip_file:
        raise TargetError(package, "Error: Target " + pkg_target.getCanonicalName() \
            + " does not generate a package tarball. (Did you want an IncludeOutput?)")
      package.resolved_input_file(zip_file)
    else:
      assembly_dir = pkg_target.get_assembly_dir()
      package.resolved_input_dir(assembly_dir)


  def emitPackageOps(self, package):

    if self.dest_dir == None:
      dest_dir = paths.OUTDIR_QUALIFIER
    else:
      dest_dir = self.dest_dir

    dest_dir = package.normalize_user_path(dest_dir, is_dest_path=True)

    pkgTarget = package.getTargetByName(self.target_name)
    if pkgTarget == None:
      raise TargetError(package, "Target not found: " + self.target_name)

    if self.include_zip:
      # just copy the zipfile into the destination
      # determine the name of the zip file from the package target
      try:
        zipFileName = pkgTarget.getPackageZip()
      except:
        raise TargetError(package, "Target " + self.target_name \
            + " is not a package target (did you want an IncludeOutput?)")

      if zipFileName == None:
        raise TargetError(package, "Error: Target " + pkg_target.getCanonicalName() \
            + " does not generate a package tarball. (Did you want an IncludeOutput?)")

      text = """
  <mkdir dir="%(destdir)s" />
  <exec executable="rsync" failonerror="true">
    <arg value="-r" />
    <arg value="--update" />
    <arg value="--copy-links" />
    <arg value="--perms" />
    <arg value="--times" />
    <arg value="%(zipfile)s" />
    <arg value="%(destdir)s" />
  </exec>
  """ % \
      {  "destdir" : dest_dir,
         "zipfile" : zipFileName
      }
    else:
      src_dir = pkgTarget.get_assembly_dir()

      text = """
  <mkdir dir="%(destdir)s" />
  <exec executable="rsync" failonerror="true">
    <arg value="-r" />
    <arg value="--update" />
    <arg value="--copy-links" />
    <arg value="--perms" />
    <arg value="--times" />
    <arg value="%(srcdir)s" />
    <arg value="%(destdir)s" />
  </exec>
      """ % \
      {  "destdir" : dest_dir,
         "srcdir"  : src_dir }

    return text

class IncludeOutput(step.Step):
  """ Incorporate the output objects from a build-phase target into a package:
      Inputs:
        target_name  -- The name of the target to run the build action on
                       and include
        dest_dir    -- Where its data goes. default is right in the assembly
                       dir
  """

  def __init__(self, target_name, dest_dir=None):
    step.Step.__init__(self)
    self.target_name = target_name
    self.dest_dir = dest_dir


  def resolve(self, package):
    target = package.getTargetByName(self.target_name)
    copySources = target.outputPaths()
    for src in target.outputPaths():
      if src.endswith(os.sep):
        package.resolved_input_dir(src)
      else:
        package.resolved_input_file(src)


  def getDependencies(self):
    return [ self.target_name ]

  def emitPackageOps(self, package):
    if self.dest_dir == None:
      dest_dir = paths.OUTDIR_QUALIFIER
    else:
      dest_dir = self.dest_dir

    dest_dir = package.normalize_user_path(dest_dir, is_dest_path=True)

    inTarget = package.getTargetByName(self.target_name)
    if inTarget == None:
      raise TargetError(package, "Target not found: " + self.target_name)

    text = ""
    copySources = inTarget.outputPaths()
    if len(copySources) > 0:
      text = text + "<mkdir dir=\"%(destdir)s\" />\n" % {  "destdir" : dest_dir }
      for src in copySources:
        text = text + """
  <exec executable="rsync" failonerror="true">
    <arg value="-r" />
    <arg value="--update" />
    <arg value="--copy-links" />
    <arg value="--perms" />
    <arg value="--times" />
    <arg value="%(src)s" />
    <arg value="%(destdir)s" />
  </exec>""" % {
          "src" : src,
          "destdir" : dest_dir
        }

    return text

