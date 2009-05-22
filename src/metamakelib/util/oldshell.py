# (c) Copyright 2009 Cloudera, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# commands to execute shell commands and the like.
#
################################################
# This module is deprecated
# New code should not depend on this module
################################################

import os
import sys
import string


from metamakelib.util.shellflags import ShellFlags

class CommandError(Exception):
  " Errors when running a shell cmd "
  def __init__(self, value):
    self.value = value

  def __str__(self):
    return repr(self.value)


def emptyFlags():
  """ return an empty flags structure that we can read """
  return ShellFlags()


def escapeSpaceChar(char):
  """ escapes space chars """
  if char == " ":
    return "\ "
  else:
    return char

def escapeSpaces(str):
  """ escapes all spaces in str """
  out = map(escapeSpaceChar, str)
  return string.join(out, "")


def sh(command, flags):
  """ run 'command' and send all output to stdout.
  Returns 0 on success, CommandError(returncode) if the return
  code is nonzero."""

  flags = emptyFlags().loadFlags(flags)
  if flags.printShellCmd:
    print command

  handle = os.popen(command + " 2>&1", "r")
  while True:
    line = handle.readline()
    if line == '':
      break
    print line.rstrip()
  ret = handle.close()
  if ret > 0:
    raise CommandError(ret)
  return 0


def shLines(command, flags):
  """ run 'command' and return all output lines.
    If command returns exceptionally, raise CommandError
    with the error return code """

  flags = emptyFlags().loadFlags(flags)
  if flags.printShellCmd:
    print command

  handle = os.popen(command + " 2>&1", "r")
  lines = handle.readlines()
  ret = handle.close()
  if ret > 0:
    raise CommandError(ret)
  return lines

def shLinesAndRet(command, flags):
  """ runs 'command' and return all output lines and the
      exit code. Do not ever raise CommandError. """

  flags = emptyFlags().loadFlags(flags)
  if flags.printShellCmd:
    print command

  handle = os.popen(command + " 2>&1", "r")
  lines = handle.readlines()
  ret = handle.close()
  if ret > 0:
    retCode = ret
  else:
    retCode = 0
  return (lines, retCode)

def pipeTo(command, stdinData, flags):
  """ runs 'command' and passes stdinData on stdin.
      Returns the exit status code. """

  flags = emptyFlags().loadFlags(flags)
  if flags.printShellCmd:
    print command

  handle = os.popen(command + " 2>&1 > /dev/null", "w")
  handle.write(stdinData)
  ret = handle.close()
  if ret > 0:
    retCode = ret
  else:
    retCode = 0
  return retCode



def scpSend(server, localPath, remotePath, flags):
  """ copy a file to a remote server """

  flags = emptyFlags().loadFlags(flags)
  if flags.printScpCmd:
    print localPath + " -> " + server + ":" + remotePath

  sshOpts = getattr(flags, "sshopts", "")

  user = flags.username

  cmd = "scp " + sshOpts + " " + escapeSpaces(localPath) + " " \
      + user + "@" + server + ":" + remotePath
  sh(cmd, flags)


def ssh(server, command, flags):
  """ run 'command' on server and send all output to stdout.
  Returns 0 on success, CommandError(returncode) if the return
  code is nonzero."""

  flags = emptyFlags().loadFlags(flags)
  if flags.printShellCmd:
    print command

  sshOpts = getattr(flags, "sshopts", "")

  user = flags.username

  handle = os.popen("ssh " + sshOpts + " " + user + "@" + server \
      + " \"" + command + "\" 2>&1", "r")
  while True:
    line = handle.readline()
    if line == '':
      break
    print line.rstrip()
  ret = handle.close()
  if ret > 0:
    raise CommandError(ret)
  return 0


def sshLines(server, command, flags):
  """ run 'command' on server and return the lines it printed
  to stdout on success, raise CommandError(returncode) if the return
  code is nonzero."""

  flags = emptyFlags().loadFlags(flags)
  if flags.printShellCmd:
    print command

  sshOpts = getattr(flags, "sshopts", "")

  user = flags.username

  handle = os.popen("ssh " + sshOpts + " " + user + "@" + server \
      + " \"" + command + "\" 2>&1", "r")
  lines = handle.readlines()
  ret = handle.close()
  if ret > 0:
    raise CommandError(ret)
  return lines


