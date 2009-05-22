# (c) Copyright 2009 Cloudera, Inc.
#
# hadoopcomponent.py
# Defines the CompileHadoopStep type which incorporates Hadoop compilation
# into a package.

import os

import metamakelib.steps.step as step

class CompileHadoopStep(step.Step):
  """ Applies a set of patches to a version of Hadoop and builds a custom
      distribution.

      hadoop_dir         Opt - Directory containing Hadoop to patch (if empty, assumes
                               the package path)
      base_version       Opt - String to use as base version (e.g. "0.18.2")
      patch_version      Opt - Suffix to the version string used internally
                               in Hadoop to denote the patch level used here.
      patch_plan         Opt - A list of patch files to apply to Hadoop
                               before compiling
  """


  def __init__(self, hadoop_dir=None, base_version="3.1.4.1.5.9", patch_version=None,
      patch_plan=[]):
    step.Step.__init__(self)
    self.hadoop_dir = hadoop_dir
    self.base_version = base_version
    self.patch_version = patch_version
    self.patch_plan = patch_plan

  def register(self, package):
    """ Hadoop packages have special versioning that doesn't use a normal
        VerStringTarget reference from the package.
    """
    package.register_version_string(self.getVerString())

  def resolve(self, package):
    # We depend on all files in the patch_plan
    # NOTE(aaron): This assumes that hadoop_dir is inside the sphere of
    # its own assembly dir, so the input files to that dir must be
    # uptodate-guarded by other CopyDirs, etc.
    for patch_file in self.patch_plan:
     package.resolved_input_file( \
         package.normalize_user_path(patch_file, is_dest_path=False, include_basedir=False))


  def get_hadoop_dir(self):
    """ Return the user-specified hadoop dir, or None if the user didn't specify one """
    return self.hadoop_dir


  def __applyPatch(self, package, patchFile, dest_dir):
    """ return the rule text to apply the named patch file """
    text = "  <exec executable=\"patch\" dir=\"" + dest_dir + "\"" \
        + " fail_on_error=\"true\">\n"
    text = text + "    <arg value=\"-p0\" />\n"
    text = text + "    <arg value=\"--forward\" />\n"
    text = text + "    <arg value=\"-i\" />\n"
    text = text + "    <arg value=\"" + package.normalize_user_path(patchFile) + "\" />\n"
    text = text + "  </exec>\n"

    return text


  def getVerString(self):
    """ return the "version" component of the assembly name"""
    version = self.base_version
    if self.patch_plan != None and len(self.patch_plan) > 0:
      version = version + "-patched"
    return version


  def emitPackageOps(self, package):

    # Directories where Hadoop will be patched and built from.
    if self.hadoop_dir != None:
      hadoop_dest_dir = package.normalize_user_path(self.hadoop_dir, is_dest_path=False)
    else:
      hadoop_dest_dir = package.get_assembly_dir()

    # create the output package dir
    text = "  <mkdir dir=\"" + hadoop_dest_dir + "\" />\n"

    # Apply patches and set the version number
    version = self.getVerString()
    for patch in self.patch_plan:
      text = text + self.__applyPatch(package, patch, hadoop_dest_dir)

    # parameters we set in Hadoop build process:
    #   "version"  is set to base_version-patch_version (e.g., 0.18.2-CH-4000)
    #              This is what "bin/hadoop version" should report
    # "final.name" is set to base_version[-patched]; this is used in the jar
    #              and tar.gz filenames.
    # Compile with -Dversion=($version)
    fullVersion = self.base_version
    if self.patch_version != None and len(self.patch_version) > 0:
      fullVersion = fullVersion + "-" + str(self.patch_version)
    text = text + "  <exec executable=\"${ant-exec}\"\n"
    text = text + "    failonerror=\"true\"\n"
    text = text + "    dir=\"" + hadoop_dest_dir + "\">\n"
    text = text + "    <arg value=\"-Dversion=" + fullVersion + "\" />\n"
    text = text + "    <arg value=\"-Dfinal.name=hadoop-" + version + "\" />\n"
    text = text + "    <arg value=\"package\" />\n"
    text = text + "  </exec>\n"

#    # Run Hadoop's internal tar-up command.
#    text = text + "  <exec executable=\"${ant-exec}\"\n"
#    text = text + "    failonerror=\"true\"\n"
#    text = text + "    dir=\"" + hadoop_dest_dir + "\">\n"
#    text = text + "    <arg value=\"-Dversion=" + fullVersion + "\" />\n"
#    text = text + "    <arg value=\"-Dfinal.name=hadoop-" + version + "\" />\n"
#    text = text + "    <arg value=\"tar\" />\n"
#    text = text + "  </exec>\n"

    return text
