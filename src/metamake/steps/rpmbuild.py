# (c) Copyright 2009 Cloudera, Inc.

import re

import metamake.steps.step as step

class RpmBuild(step.Step):
  """ Creates on RPM for a package """

  def __init__(self, spec_file, rpm_build_cmd="-bb", rpm_release="1", sources=[]):
    step.Step.__init__(self)
    self.spec_file = spec_file
    self.rpm_build_cmd = rpm_build_cmd
    self.rpm_release = rpm_release
    self.sources = sources

  def resolve(self, package):
    # NOTE(aaron): Assumes all inputs to the rpm itself are already
    # inside the package assembly dir and guarded by their own
    # uptodate checks. If this is wrong, then we need to add an
    # inputs list to this object as well and/or support forced builds
    # a la Exec.
    package.resolved_input_file( \
        package.normalize_user_path(self.spec_file, is_dest_path=False, include_basedir=False))
    for source in self.sources:
      package.resolved_input_file( \
          package.normalize_user_path(source, is_dest_path=False, include_basedir=False))


  def emitPackageOps(self, package):
    source_copies = "\n".join([
      """
      <copy file="%s"
            todir="${rpmdir}/SOURCES/"
            overwrite="yes"/>
      """ % package.normalize_user_path(source_file)
      for source_file in self.sources])

    text = """
  <!-- Create the RPM build skeleton -->
  <mkdir dir="${rpmdir}/RPMS" />
  <mkdir dir="${rpmdir}/SPECS" />
  <mkdir dir="${rpmdir}/SOURCES" />
  <mkdir dir="${rpmdir}/BUILD" />
  <mkdir dir="${rpmdir}/SRPMS" />
  <mkdir dir="${rpmdir}/INSTALL" />

  <!-- Copy the package spec file into the RPM spec directory -->
  <copy file="%(spec_file)s"
        tofile="${rpmdir}/SPECS/%(pkgName)s-%(rpmVersion)s.spec"
        overwrite="yes"/>

  <!-- Copy the sources -->
  %(source_copies)s

  <!-- Replace the following tokens in the RPM spec file -->
  <replace file="${rpmdir}/SPECS/%(pkgName)s-%(rpmVersion)s.spec">
          <replacefilter
                  token="@VERSION@"
                  value="%(version)s" />
          <replacefilter
      token="@RPMVERSION@"
                  value="%(rpmVersion)s" />
          <replacefilter
                  token="@RELEASE@"
                  value="%(release)s" />
          <replacefilter
                  token="@PKGROOT@"
                  value="%(pkgRoot)s" />
          <replacefilter
                  token="@RPMBUILDROOT@"
                  value="${rpmdir}/INSTALL" />
  </replace>

  <rpm
          specfile="%(pkgName)s-%(rpmVersion)s.spec"
          topDir="${rpmdir}"
          cleanBuildDir="yes"
          removeSpec="no"
          removeSource="yes"
          failOnError="yes"
          command="%(rpm_build_cmd)s" />

""" % {
     "spec_file": package.normalize_user_path(self.spec_file),
     "pkgName": package.get_package_name(),
     "pkgRoot": package.get_assembly_dir(),
     "version": package.getVerString(),
     "rpmVersion": re.sub('-','_', package.getVerString()),
     "rpm_build_cmd": self.rpm_build_cmd,
     "release": self.rpm_release,
     "source_copies": source_copies
      }

    return text
