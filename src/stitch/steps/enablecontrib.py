# (c) Copyright 2009 Cloudera, Inc.
#
# enablecontrib.py
# defines the EnableContrib object

import os

import stitch.steps.step as step

class EnableContrib(step.Step):
  """ This Step is only valid within the scope of a HadoopPackageTarget.
      It tells the Hadoop Package Target to include the jar output of a contrib
      item in the built Hadoop's lib/ dir.

      Also, looks in src/contrib/${name}/lib/ for any jars and includes them
      as well.

      Inputs:
        name         -- The name of the contrib item (e.g. src/contrib/${name})
        compile_step -- The step which performs Hadoop compilation
  """

  def __init__(self, name, compile_step):
    step.Step.__init__(self)
    self.name = name
    self.compile_step = compile_step


  def getDependencies(self):
    return []


  def emitPackageOps(self, package):
    """ After Hadoop is built, copy all the jar files from the named contrib
        item into the lib dir.

        If the contrib item comes with its own lib entries, include these
        too. (Since this is optional; failonerror is false so no problem
        if src/contrib/$name/lib does not exist.
    """

    hadoop_dir = self.compile_step.get_hadoop_dir()
    if hadoop_dir == None:
      hadoop_dir = package.get_assembly_dir()

    buildDir = os.path.join(hadoop_dir, "build", "contrib", self.name)
    targetDir = os.path.join(hadoop_dir, "build", \
        "hadoop-" + self.compile_step.getVerString(), "lib")
    srcLibDir = os.path.join(hadoop_dir, "src", "contrib", self.name, "lib")

    return """
  <copy todir="%(targetdir)s">
    <fileset dir="%(builddir)s">
      <include name="*.jar" />
    </fileset>
  </copy>
  <copy todir="%(targetdir)s" failonerror="false">
    <fileset dir="%(srclibdir)s">
      <include name="*.jar" />
    </fileset>
  </copy>
    """ % { "builddir"  : buildDir,
            "srclibdir" : srcLibDir,
            "targetdir" : targetDir }


