# (c) Copyright 2009 Cloudera, Inc
#
# module: stitch.steps.tar
#
# Tars up the package assembly directory into a tarball.

import os

import stitch.steps.step as step


class Tar(step.Step):
  """ Replaces the default tar action of a PackageTarget with this tar action.
      Allows you to control which directory is tarred, and what the final filename is.

      dir        Opt - Specifies directory to tar up (default: the assembly dir)
      filename   Opt - Tar filename to create. This should end in ".tar.gz"
                       Set to ${packagename}.tar.gz by default.
      args       Opt - If set, then dir and filename are ignored as inputs
                       to the actual tar command; args contains all the arguments
                       passed on the commandline to the tar executable.
                       filename must still be set to allow other targets to
                       depend on the output tarball.
  """

  def __init__(self, dir=None, filename=None, args=None):
    step.Step.__init__(self)
    self.dir = dir
    self.filename = filename
    self.args = args


  def register(self, package):
    package.register_output_zip(self)


  def get_tar_filename(self, package):
    pkgName = package.get_package_name() + package.getVerWithDash()
    if self.filename == None:
      tar_filename = pkgName + ".tar.gz"
    else:
      tar_filename = package.force(self.filename)

    return tar_filename


  def emitPackageOps(self, package):

    if self.args == None:
      # Use build-in tar command.
      pkgName = package.get_package_name() + package.getVerWithDash()
      if self.dir != None:
        full_path_to_grab = package.normalize_user_path(package.force(self.dir), \
            is_dest_path=True, include_basedir=False)
      else:
        full_path_to_grab = package.get_assembly_dir()

      if full_path_to_grab.endswith(os.sep):
        full_path_to_grab = full_path_to_grab[:-1]
      tar_base_path = os.path.dirname(full_path_to_grab)
      tar_subdir = os.path.basename(full_path_to_grab)

      tar_filename = os.path.join(package.get_assembly_top_dir(), self.get_tar_filename(package))

      text = """
  <exec executable="tar" failonerror="true">
    <arg value="czf" />
    <arg value="%(tarfilename)s" />
    <arg value="-C" />
    <arg value="%(basepath)s" />
    <arg value="%(tarsrcdir)s" />
  </exec>
""" % {
        "tarfilename" : tar_filename,
        "basepath"    : tar_base_path,
        "tarsrcdir"   : tar_subdir
      }
    else:
      # user set self.args; so we use all of those.
      # run tar from the package base path.
      argtext = ""
      for arg in package.force(self.args):
        arg = package.normalize_select_user_path(arg)
        arg = package.substitute_macros(arg)

        argtext = argtext + "<arg value=\"%(val)s\" />\n" % { "val" : arg }
      text = """
  <exec executable="tar" failonerror="true" dir="%(basedir)s">
%(argtext)s
  </exec>
""" % {
        "basedir" : package.get_assembly_top_dir(),
        "argtext" : argtext,
      }

    return text

