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
# Manages Cloudera-specific usage of the python 'logging' module
# Rather than use 'logging' directly, import this module instead.
# This module includes and reexports all elements of the logging module
#
# This module defines the common command-line arguments used to
# control output verbosity for stdout/stderr. Applications are encouraged
# to use these same argument names for consistency
#
# These are:
#   (VERBOSE_FLAG) --verbose, -v    Print CRITICAL through VERBOSE
#   (DEBUG_FLAG)   --debug          Print CRITICAL through DEBUG
#   (QUIET_FLAG)   --quiet, -q      Only emit CRITICAL output.
#                                   (Overrides --verbose and --debug)
#
#  Default action is to print CRITICAL through INFO
#
# Properties:
#
# The actual governing of what data is printed to the screen is handled
# by the properties object passed to the stream's constructor.
#
# The properties in question are:
#   output.quiet      Sets quiet mode
#   output.verbose    Enables verbose outputs
#   output.debug      Enables debug outputs
#
#
# The attachOutputArgParser() method will instantiate an ArgParser for
# these flags and bind it to a Properties object
#
# Your program should call initLogging() before doing virtually anything
# else. (see its comments for why). When you know what log level you want,
# you should then call setupConsole(). (In practice, these will be called
# by the ensureConsole() method if you use any of the println*() methods
# of this module.)
#
# "VERBOSE" is not defined by their logging system; in addition to
# the levels CRITICAL, ERROR, WARNING, INFO, and DEBUG (defined in
# the logging module, and re-exported here), we add a new level
# VERBOSE between INFO and DEBUG.
#
# A standard log file argument is now available. This flag (LOG_FILENAME_FLAG)
# takes as an argument the name of a log file. If present, this implies that
# the root logger should also send a copy of its output to the indicated log
# file.  This log will be installed during the call to setupConsole().
# The getAutoFileHandler() method will return the Handler object installed by
# this process. The getAutoLogName() method will return the filename used.
#
# The flag itself is "--log-filename" and sets the property output.auto.logfile.
# The verbosity level of this automatic log is handled by "--log-level" which
# sets the property output.auto.level. These flags are handled by
# attachOutputArgParser().


import atexit
from   logging import *
import sys

from   metamakelib.util.argparser import ArgParser

QUIET_PROP   = "output.quiet"
VERBOSE_PROP = "output.verbose"
DEBUG_PROP   = "output.debug"

QUIET_FLAG   = "--quiet"
VERBOSE_FLAG = "--verbose"
DEBUG_FLAG   = "--debug"

# applications that use this output framework can have their log file usage
# automatically handled by this flag.
LOG_FILENAME_FLAG = "--log-filename"
LOG_FILENAME_PROP = "output.auto.logfile"

# The verbosity level string to apply to this log file.
# Default (if unset) is whatever the screen's level is.
LOG_VERBOSITY_FLAG = "--log-level"
LOG_VERBOSITY_PROP = "output.auto.level"

# register the verbose level
VERBOSE = 15
addLevelName(VERBOSE, "VERBOSE")


# when the program terminates, clean up logs as best as possible
atexit.register(shutdown)


def attachOutputArgParser(properties):
  """ Given a Properties object, attach an arg parser that will use standard
      command-line flags to modify the above properties. These standard
      properties govern our use of the stdout stream which is set up by
      the setupConsole() method """

  argMap = {}

  # Screen verbosity level arguments
  argMap["-q"]         = QUIET_PROP
  argMap["-v"]         = VERBOSE_PROP
  argMap[DEBUG_FLAG]   = DEBUG_PROP
  argMap[QUIET_FLAG]   = QUIET_PROP
  argMap[VERBOSE_FLAG] = VERBOSE_PROP
  booleans = [ DEBUG_FLAG, QUIET_FLAG, VERBOSE_FLAG, "-q", "-v" ]

  argMap[LOG_FILENAME_FLAG] = LOG_FILENAME_PROP
  argMap[LOG_VERBOSITY_FLAG] = LOG_VERBOSITY_PROP

  argParser = ArgParser(argMap, booleans)
  properties.addArgParser(argParser)



initCalled = False

def initLogging():
  """ This should be called absolutely first in the program. This
      sets the logging system to be silent; you then call setupConsole()
      after you've determined what log level you want. The reason for
      this is because basicConfig() will be called automatically if you
      call any other logging methods; then you do not have access to
      the default handle to reconfigure it later. """
  global initCalled

  # set up the basic configuration to /dev/null
  basicConfig(level=CRITICAL, format="%(message)s", \
      filename="/dev/null", filemode="w")

  initCalled = True


def getDefaultLogLevel(properties):
  """ Returns the log level specified by the properties given """

  if properties.getBoolean(QUIET_PROP):
    return CRITICAL
  elif properties.getBoolean(DEBUG_PROP):
    return DEBUG
  elif properties.getBoolean(VERBOSE_PROP):
    return VERBOSE
  else:
    return INFO

# private internal persistent state for setupConsole
# (and how it interacts with ensureConsole)
consoleHandler = None
curConsoleLevel = None

def setupConsole(properties):
  """ Given a properties file, set up the logging module to take over
      stdout, use a reasonable format, and pick a default log level.
      This must be called every time we change the values of the properties
      which govern logging, for those properties to take effect. (An
      equally valid method is to just call getLogger().setLevel(newlevel).

      If properties is not modified, calling this method with the same
      properties object multiple times is idempotent.

      This will also look for the presence of auto log file properties. If
      these are set (and no auto log file was yet installed), this will
      install the auto logfile. If an auto logger is already installed,
      changing the properties here will have no effect. You should
      use getAutoFileHandler() to manipulate the handler it installs directly.
  """

  global consoleHandler
  global curConsoleLevel
  global initCalled

  if not initCalled:
    initLogging()

  if properties == None:
    defaultLvl = curConsoleLevel
  else:
    defaultLvl = getDefaultLogLevel(properties)

  # Set the logger to pass everything through it; we do the filtering
  # at the handlers.
  getLogger().setLevel(DEBUG)

  if defaultLvl != curConsoleLevel:
    if consoleHandler != None:
      consoleHandler.setLevel(defaultLvl)
    curConsoleLevel = defaultLvl

  if consoleHandler == None:
    formatter = Formatter("%(message)s")

    # Create a console logger
    consoleHandler = StreamHandler(sys.stdout)
    consoleHandler.setLevel(defaultLvl)
    consoleHandler.setFormatter(formatter)

    # and attach it to the root logger
    getLogger().addHandler(consoleHandler)

  if properties != None:
    setupAutoFileLogging(properties)


def ensureConsole():
  """ called by the println*() methods below to ensure that we have
      a console ready and waiting for us """
  if consoleHandler == None:
    setupConsole(None)


def installFileLogger(filename, level=None):
  """ install a handler on the root logger to output to a particular
      file. Uses the provided level. If this is None, then use the
      curConsoleLevel """
  # TODO(aaron): Consider using TimedRotatingFileHandler instead
  global curConsoleLevel

  if level == None:
    ensureConsole()
    level = curConsoleLevel

  handler = FileHandler(filename)
  handler.setFormatter(Formatter(
      "[%(asctime)s] %(levelname)s %(name)s : %(message)s"))
  handler.setLevel(level)
  getLogger().addHandler(handler)
  return handler



# if we automatically install a Handler to log to a file, stash it here.
autoFileHandler = None
def getAutoFileHandler():
  """ Return the automatically-installed root file log handler, if any """
  global autoFileHandler
  return autoFileHandler


def setupAutoFileLogging(properties):
  """ Called by setupConsole() to automatically set up a FileHandler for
      the root level logger, if the user provided us with the appropriate
      command line flags / properties. If the automatic file handler is
      already in place, repeated calls to this method do nothing. (You
      should use getAutoFileHandler() to get the handler and change its
      settings yourself. """

  if getAutoFileHandler() != None:
    # one's already installed. Do nothing more.
    return

  autoFilename = properties.getProperty(LOG_FILENAME_PROP)
  if autoFilename == None:
    # no auto logfile requested.
    return

  logLevelName = properties.getProperty(LOG_VERBOSITY_PROP)

  if logLevelName == None:
    # this wasn't set. Grab the default.
    logLevelName = getDefaultLogLevel(properties)

  # if logLevelName was set programmatically, it might be an actual
  # integer log level rather than a string. If so, just use that.
  logLevel = None
  try:
    if logLevelName == int(logLevelName):
      logLevel = logLevelName # yup
  except ValueError:
    pass # no, it was a string.

  if logLevel == None:
    logLevel = getLevelName(logLevelName)

  # getLevelName() will return a string "Level foo" if this is not a
  # registered level. Test this by making sure we got a real integer back.
  try:
    logLevelInt = int(logLevel)
    logLevelErr = False
  except ValueError:
    # The provided level string is invalid. Flag the error here (log it to the
    # file itself, later), and use the user's screen logging level.
    logLevelInt = getDefaultLogLevel(properties)
    logLevelErr = True


  # actually install the log
  global autoFileHandler
  autoFileHandler = installFileLogger(autoFilename, logLevelInt)

  printlnDebug("Opened log file " + autoFilename \
      + " for logging at level " + str(logLevelName))

  if logLevelErr:
    printlnError("No such log level " + str(logLevelName) \
        + " for --log-level; using default level of: " \
        + str(getLevelName(logLevelInt)))


# The following methods should be used instead of the 'print' statement
# throughout our code base, if you want something to go to the output
# stream as well as any underlying logs.

def printlnError(thing):
  ensureConsole()
  error(str(thing))

def printlnInfo(thing):
  ensureConsole()
  info(str(thing))

def printlnVerbose(thing):
  ensureConsole()
  log(VERBOSE, str(thing))

def printlnDebug(thing):
  ensureConsole()
  debug(str(thing))

def printlnLevel(level, thing):
  ensureConsole()
  log(level, str(thing))


