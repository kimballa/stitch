# (c) Copyright 2009 Cloudera, Inc.
#
# antcall.py
# Defines the AntCall type which invokes an ant target inside the assembly directory
# of a package to perform additional compilation.

import os

import stitch.steps.step as step

class AntCall(step.Step):
  """ Runs ant inside the package assembly directory

      ant_target         Opt - Name of an ant target to run
      base_dir           Opt - directory to run ant in
      build_file         Opt - Buildfile to use instead of ${base_dir}/build.xml
      properties        Opt - Dictionary of key=val properties to pass to ant
      force_build       Opt - Force the package to rebuild (default False)
  """

  def __init__(self, ant_target=None, base_dir=None, build_file=None, properties=None,
               force_build=False):
    step.Step.__init__(self)

    self.ant_target = ant_target
    self.base_dir = base_dir
    self.build_file = build_file
    self.properties = properties
    self.force_build = force_build

  def resolve(self, package):
    # Cannot introspect for uptodate.
    # TODO(aaron): Allow them to provide an up-to-date target to run.
    if self.force_build:
      package.resolved_forced_build()


  def emitPackageOps(self, package):
    text = ""
    text = text + "  <exec executable=\"${ant-exec}\"\n"
    text = text + "    failonerror=\"true\"\n"
    if self.base_dir == None:
      # Run ant wherever we're doing the assembly.
      text = text + "    dir=\"" + package.get_assembly_dir() + "\">\n"
    else:
      text = text + "    dir=\"" \
          + package.normalize_user_path(package.force(self.base_dir), is_dest_path=True) + "\">\n"

    if self.build_file != None:
      text = text + "    <arg value=\"-f\" />\n"
      text = text + "    <arg value=\"" \
          + package.normalize_user_path(package.force(self.build_file)) + "\" />\n"

    if self.properties != None:
      for prop_name in self.properties:
        prop_val = package.force(self.properties[prop_name])
        prop_arg = "-D" + prop_name + "=" + prop_val
        text = text + "     <arg value=\"" + prop_arg + "\" />\n"

    if self.ant_target != None:
      text = text + "    <arg value=\"" + package.force(self.ant_target) + "\" />\n"

    text = text + "  </exec>\n"
    return text


