# (c) Copyright 2009 Cloudera, Inc.
#
# rsynctarget.py
# Defines RsyncTarget, which retrieves a file from a central remote repository
# into the bin dir.

import os

from   stitch.targets.targeterror import TargetError
from   stitch.targets.target import *
from   stitch.targets.anttarget import *

class RsyncTarget(AntTarget):
  """ Retrieves a remote package file from the central package repository.

      phase: build

      filename       Req - The file to retrieve
      md5sum         Req - The expected MD5 sum of the file.
  """

  def __init__(self, filename, md5sum):
    AntTarget.__init__(self)

    self.required_targets = None
    self.filename = filename
    self.md5sum = md5sum

  def generates_preamble(self):
    return True

  def preamble(self):
    return self.emit_output_pathref()

  def language(self):
    return "none"


  def outputPaths(self):
    return [ "${local-rsync-cache}/" + self.filename ]


  def get_ant_rule_map(self):
    return {
      "build" : self.getSafeName() + "-build",
      "default" : self.getSafeName() + "-build"
    }



  def antRule(self, rule):
    """ generates the XML to put in the buildfile
        for the ant rule """

    if rule == "preamble":
      return self.preamble()

    (mainName, ruleType) = self.splitRuleName(rule)

    text = "<target name=\"" + rule + "\" "
    depAntRules = self.getAntDependencies(ruleType)
    text = text + depAntRules + ">\n"

    # The logic for this block is as follows:
    # First the MD5 of the cached copy (if it exists) is compared to the MD5
    # expected by the Target. if they match, no further action is taken.
    # Otherwise, it downloads a new copy via rsync, and re-checks the MD5 sum.
    # Note the "{md5-output-file}.0" vs "{md5-output-file}.1" in the diff cmds.
    text = text + """
  <mkdir dir="${local-rsync-cache}" />
  <exec executable="md5sum" failonerror="false" output="${md5-output-file}.%(filename)s.0"
      dir="${local-rsync-cache}" resultproperty="ignored.md5.result">
    <arg value="%(filename)s" />
  </exec>
  <echo file="${md5-output-file}.%(filename)s.good" message="%(md5sum)s  %(filename)s" />
  <exec executable="diff" failonerror="false" resultproperty="diff.initial.%(rulename)s"
      outputproperty="diff.output">
    <arg value="-q" />
    <arg value="-w" />
    <arg value="-B" />
    <arg value="${md5-output-file}.%(filename)s.0" />
    <arg value="${md5-output-file}.%(filename)s.good" />
  </exec>
  <if>
    <bool>
      <not>
        <equals arg1="${diff.initial.%(rulename)s}" arg2="0" />
      </not>
    </bool>
    <exec executable="rsync" failonerror="true">
      <arg value="--verbose" />
      <arg value="--copy-links" />
      <arg value="--compress" />
      <arg value="--update" />
      <arg value="--perms" />
      <arg value="--times" />
      <arg value="${rsync-upstream-source}/%(filename)s" />
      <arg value="${local-rsync-cache}/%(filename)s" />
    </exec>
    <exec executable="md5sum" failonerror="true" output="${md5-output-file}.%(filename)s.1"
        dir="${local-rsync-cache}">
      <arg value="%(filename)s" />
    </exec>
    <exec executable="diff" failonerror="false" resultproperty="diff.result.%(rulename)s"
        outputproperty="diff.output">
      <arg value="-q" />
      <arg value="-w" />
      <arg value="-B" />
      <arg value="${md5-output-file}.%(filename)s.1" />
      <arg value="${md5-output-file}.%(filename)s.good" />
    </exec>
    <if>
      <bool>
        <not>
          <equals arg1="${diff.result.%(rulename)s}" arg2="0" />
        </not>
      </bool>
      <fail message="MD5 mismatch for ${local-rsync-cache}/%(filename)s; expected %(md5sum)s" />
    </if>
  </if>
""" % { "filename" : self.filename,
        "md5sum"   : self.md5sum,
        "rulename" : rule }

    text = text + "</target>\n"
    return text


