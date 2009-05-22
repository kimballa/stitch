#!/usr/bin/env python
#
# (c) Copyright 2009 Cloudera, Inc.

"""
  Usage: makeVer.py
      --basepath path               Path to genfiles root
      --modname modulename          Name of python module or Java class
      --lang { python | java }      Target language to emit
      --verstring version-string    The version string to insert
"""

__usage = """
  Creates a module in either python or Java that contains the
  supplied version string, for inclusion in other programs.
"""


import optparse
import os
import sys

# If they don't pass us --modname, what to use?
DEFAULT_MODULE_NAME = "verinfo"

# If they don't pass us --basepath, what to use?
DEFAULT_BASE_PATH = "."


def parse_options():
  """ Use optparse to parse the argv options. Returns the 'options' object
      and the parser used to generate it.
  """

  global __usage
  global DEFAULT_MODULE_NAME
  global DEFAULT_BASE_PATH

  parser = optparse.OptionParser(usage=__usage)

  parser.add_option("-b", "--basepath", dest="basepath",
      default=DEFAULT_BASE_PATH,
      help="Path to genfiles root")
  parser.add_option("-m", "--modname", dest="modname",
      default=DEFAULT_MODULE_NAME,
      help="Name of python module or Java class to build")
  parser.add_option("-L", "--lang", dest="lang",
      help="Target language to emit ('java' or 'python')")
  parser.add_option("-s", "--verstring", dest="verstring",
      help="The version string to insert")

  (options, args) = parser.parse_args()
  return (options, parser)



def get_mod_filename(options, ext=""):
  """ Return the path to the module file. The filename ends with 'ext',
      e.g., ".java". Creates any necessary directories.
  """
  # Create the directory where the module goes and figure out its filename.
  mod_steps = options.modname.split(".")
  dir_steps = mod_steps[0:len(mod_steps) - 1]
  module_name = mod_steps[-1]
  mod_dirs = reduce(lambda acc, x: os.path.join(acc, x), dir_steps, "")

  all_dir_parts = os.path.join(options.basepath, mod_dirs)
  os.system("mkdir -p " + all_dir_parts)
  mod_filename = os.path.join(all_dir_parts, module_name + ext)

  return mod_filename


def make_java(options):
  """ Create a Java class containing the version string """

  mod_filename = get_mod_filename(options, ".java")

  mod_steps = options.modname.split(".")
  pkg_parts = mod_steps[0:len(mod_steps) - 1]
  if len(pkg_parts) > 0:
    package_name = reduce(lambda acc, x: acc + "." + x, pkg_parts[1:], pkg_parts[0])
  else:
    package_name = None

  if package_name == None:
    package_def = ""
  else:
    package_def = "package " + package_name + ";"

  class_name = mod_steps[-1]

  handle = open(mod_filename, "w")
  handle.write("""// (c) Copyright 2009 Cloudera, Inc.
// WARNING: This file is AUTO-GENERATED.
// Do not edit!

%(pkgdefinition)s

public final class %(classname)s {
  private static final String VERSION_STRING = "%(verstring)s";

  private %(classname)s() { }

  public static String getVersionStr() {
    return VERSION_STRING;
  }
}

""" % {  "pkgdefinition" : package_def,
         "classname"     : class_name,
         "verstring"     : options.verstring
    })

  handle.close()


def make_python(options):
  """ Create a python module containing the version string """

  mod_filename = get_mod_filename(options, ".py")

  handle = open(mod_filename, "w")
  handle.write("""#!/usr/bin/env python
# (c) Copyright 2009 Cloudera, Inc.
# WARNING: This file is AUTO-GENERATED.
# Do not edit!

__VERSION_STRING = "%(verstring)s"

def get_version():
  global __VERSION_STRING
  return __VERSION_STRING

if __name__ == "__main__":
  print get_version()

""" % { "verstring" : options.verstring })

  handle.close()


def main(argv):

  (options, parser) = parse_options()

  if options.verstring == None:
    parser.error("--verstring is required.")
    return 1

  if options.lang == "java":
    make_java(options)
  elif options.lang == "python":
    make_python(options)
  elif options.lang == None:
    parser.error("Missing required argument --lang")
    return 1
  else:
    parser.error("--lang must be one of 'python' or 'java'.")
    return 1

  return 0


if __name__ == "__main__":
  ret = main(sys.argv)
  sys.exit(ret)

