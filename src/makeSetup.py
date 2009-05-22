#!/usr/bin/env python
#
# (c) Copyright 2009 Cloudera, Inc.

"""
  Usage: makeSetup.py
      --name package_name            Name of the component being distributed.
      --verstring version            Version string applied to the component.
      --outfile filename             Path to the output setup.py script to write.
      --srcdir path                  Root path to python sources to include.
                                     Maybe a comma-separated list of multiple roots.
      --datafiles path               A string that defines what data files to include
                                     and where they should be installed.  See
                                     --help for details.
      --basedir path                 Root path to the installation; srcdir is relative
                                     to this.
"""

__usage = """
  Creates a distutils setup.py script that installs the package created by a
  PythonRedistTarget.
"""


import optparse
import os
import sys


def parse_options():
  """ Use optparse to parse the argv options. Returns the 'options' object
      and the parser used to generate it.
  """

  global __usage
  global DEFAULT_MODULE_NAME
  global DEFAULT_BASE_PATH

  parser = optparse.OptionParser(usage=__usage)

  parser.add_option("-n", "--name", dest="package_name",
      default="(none)",
      help="Name of this package")
  parser.add_option("-v", "--verstring", dest="version_string",
      default=None,
      help="Version string applied to this package")
  parser.add_option("-f", "--outfile", dest="outfile",
      default="setup.py",
      help="Output filename to write")
  parser.add_option("-s", "--srcdir", dest="srcdir",
      default=".",
      help="Path (relative to basedir) to source scripts/packages.")
  parser.add_option("-b", "--basedir", dest="basedir",
      default=os.getcwd(),
      help="Root path to the package being assembled")
  parser.add_option("-d", "--datafiles",
      help="A file that contains a list of data files of the form. srcFile\tdestFile\nsrcFile2\tdestFile2")

  (options, args) = parser.parse_args()
  return (options, parser)


def is_python_script(filename):
  """ Returns true if the file's first line matches "#!.*python" """

  handle = open(filename)
  line = handle.readline()
  handle.close()
  return line.startswith("#!") and line.find("python") != -1


def find_sources(srcdir, package_prefix=''):
  """ Return two lists:
      The first contains all packages (directories containing __init__.py files);
      the second contains all files whose first line matches  "#!.*python"
      in the directory indicated by the srcdir argument.

      This is recursive.
      package_prefix defines the component of the current package name
      indicated by the srcdir. This is '' for the root srcdir.
  """

  packages = []
  scripts = []
  subdirs = []

  files = os.listdir(srcdir)
  for file in files:
    if os.path.isdir(os.path.join(srcdir, file)):
      # Add this to the list to recurse into.
      subdirs.append(file)
    elif file == "__init__.py":
      # This is a package.
      packages.append(package_prefix)
    elif is_python_script(os.path.join(srcdir, file)):
      # Turn the package name into path steps
      script_prefix = package_prefix.replace(".", os.path.sep)
      if len(script_prefix) > 0:
        script = script_prefix + os.path.sep + file
      else:
        script = file
      scripts.append(script)


  # Recurse into all subdirectories we find.
  for subdir in subdirs:
    fullsubdir = os.path.join(srcdir, subdir)
    if len(package_prefix) > 0:
      child_package = package_prefix + "." + subdir
    else:
      child_package = subdir

    (new_packages, new_scripts) = find_sources(fullsubdir, child_package)
    packages.extend(new_packages)
    scripts.extend(new_scripts)

  return (packages, scripts)


def find_datafiles_in_dir(srcdir, subdir_prefix=''):
  """ Return the list of files in srcdir

      This is recursive.
      subdir_prefix is used by recursive calls to construct the full
      filename of the files we find in srcdir under the original srcdir
      we started traversing.
      This is '' for the root srcdir.
  """

  outfiles = []
  subdirs = []

  files = os.listdir(srcdir)
  files.sort() # enforce deterministic order for unit tests.
  for file in files:
    if os.path.isdir(os.path.join(srcdir, file)):
      # Add this to the list to recurse into.
      subdirs.append(file)
    else:
      outfiles.append(os.path.join(subdir_prefix, file))

  # Recurse into all subdirectories we find.
  for subdir in subdirs:
    fullsubdir = os.path.join(srcdir, subdir)
    if len(subdir_prefix) > 0:
      child_prefix = subdir_prefix + os.sep + subdir
    else:
      child_prefix = subdir

    new_files = find_datafiles_in_dir(fullsubdir, child_prefix)
    outfiles.extend(new_files)

  return outfiles


def datafiles_map(datafiles_path, basedir):
  """
  Takes a path to a file that specifies which data files to include and returns a map,
  where keys are src files and values are destination dirs.  The datafiles_path file is
  of the form:

  srcFile1\tdestDir1
  srcFile2\tdestDir2

  if one of the srcFile components ends with "/**", then it actually expands
  to all files in all subdirs of the dir represented by srcFile.

  The filenames input to this method may be absolute paths. They are chomped and
  made relative to basedir, which is usually set to os.getcwd()
  """
  fh = open(datafiles_path, 'r')
  ret = {}
  lines = 0
  try:
    for pair in fh:
      parts = pair.strip().split("\t")
      srcFile, destDir = parts[0], parts[1]
      if srcFile.endswith("**"):
        # hack off the "**" suffix
        src_dir = srcFile[:-2]
        # and find all the files under there
        recursive_files = find_datafiles_in_dir(src_dir)
        for file in recursive_files:
          ret[os.path.join(src_dir, file)] = os.path.join(destDir, os.path.dirname(file))
      elif ret.get(srcFile):
        raise Exception("A data file is defined twice!")
      else:
        ret[srcFile] = destDir
      lines += 1
  finally:
    fh.close()
  if not lines:
    return {}

  # make everything relative to basedir if one was set.
  if basedir:
    if not basedir.endswith(os.sep):
      basedir = basedir + os.sep

    relative_ret = {}
    for (src_file, dest_dir) in ret.iteritems():
      common_pre = os.path.commonprefix([basedir, src_file])
      relative_file = src_file[len(common_pre):]
      relative_ret[relative_file] = dest_dir

    ret = relative_ret

  return ret

def datafiles_str_map(datafiles_path, basedir):
  """
  Takes a path to a file that specifies which data files to include and returns a map
  meant to be flattened to a list included in setup.py.  The datafiles_path file is
  of the form:

  srcFile1\tdestDir1
  srcFile2\tdestDir2

  The returned map has type:
     destDir (string) -> srcfiles (string list)
  """
  # datafiles_map is a map of srcfile (string) -> destdir (string)
  in_map = datafiles_map(datafiles_path, basedir)

  # create a map of destdir (string) -> srcfiles (string list)
  out_map = {}

  for (src_file, dest_dir) in in_map.iteritems():
    srcfiles_list = out_map.get(dest_dir)
    new_item = False
    if not srcfiles_list:
      new_item = True
      srcfiles_list = []

    srcfiles_list.append(src_file)
    if new_item:
      out_map[dest_dir] = srcfiles_list

  return out_map

def datafiles_str(datafiles_path, basedir):
  # create a string rep. of the list emitted by flattening out_map generated by datafiles_str_map.
  return str(datafiles_str_map(datafiles_path, basedir).items())


def make_setup(options):
  """ Make the setup.py script """

  package_name = options.package_name

  if options.version_string != None:
    version_string = "version=\"" + options.version_string + "\","
  else:
    version_string = ""

  full_basedir = os.path.abspath(options.basedir) + os.sep
  full_srcdir = os.path.abspath(os.path.join(options.basedir, options.srcdir)) + os.sep

  pathprefix = os.path.commonprefix([full_basedir, full_srcdir])
  if len(pathprefix) == 0:
    print "Warning: common path prefix between basedir and srcdir is empty."
    print "This probably means that package name information will be mangled"
    print "in this deployment."

  srcdir_prefix = full_srcdir[len(pathprefix):]
  if len(srcdir_prefix) > 0:
    package_dir_str = "package_dir = { '' : \"" + srcdir_prefix + "\" },"
  else:
    package_dir_str = ""

  (packages, scripts) = find_sources(options.srcdir)
  datafiles = datafiles_str(options.datafiles, os.getcwd())

  if len(packages) > 0:
    packages_str = "packages = " + str(packages) + ","
  else:
    packages_str = ""

  if len(scripts) > 0:
    if len(srcdir_prefix) > 0:
      # srcdir prefix needs to be applied to all scripts
      newscripts = []
      for script in scripts:
        newscripts.append(os.path.join(srcdir_prefix, script))
      scripts = newscripts

    scripts_str = "scripts = " + str(scripts) + ","
  else:
    scripts_str = ""

  if datafiles:
    datafiles = "data_files = %s," % datafiles

  setup_script_file = os.path.abspath(options.outfile)
  manifest_in_file = os.path.join(os.path.dirname(setup_script_file), "MANIFEST.in")

  # Write the setup.py file
  handle = open(setup_script_file, "w")
  handle.write("""#!/usr/bin/env python
# (c) Copyright 2009 Cloudera, Inc.
#
# setup script for package %(packagename)s.
# To install, run 'python setup.py install'
# Warning: This file is AUTOGENERATED. Do not edit!

from distutils.core import setup

setup(name="%(packagename)s",
  %(verstring)s
  url = "http://www.cloudera.com",
  maintainer = "Cloudera",
  maintainer_email = "eng@cloudera.com",
  %(packagedir)s
  %(packages)s
  %(scripts)s
  %(datafiles)s
  )

""" % { "packagename" : package_name,
        "verstring"   : version_string,
        "packagedir"  : package_dir_str,
        "packages"    : packages_str,
        "scripts"     : scripts_str,
        "datafiles"   : datafiles,
      })
  handle.close()

  # Write the MANIFEST.in file to include any data paths.
  datafiles = datafiles_map(options.datafiles, os.getcwd())
  if datafiles:
    handle = open(manifest_in_file, "w")
    for (file, outdir) in datafiles.iteritems():
      handle.write("include " + file + "\n")
    handle.close()


def main(argv):

  (options, parser) = parse_options()
  make_setup(options)
  return 0


if __name__ == "__main__":
  ret = main(sys.argv)
  sys.exit(ret)

