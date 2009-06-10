# (c) Copyright 2009 Cloudera, Inc.
#
# module: filesteps
""" contains Step operations that manipulate files and directories """


import os

import stitch.paths as paths
from   stitch.targets.targeterror import TargetError
import stitch.steps.step as step

class CopyFile(step.Step):
  """ Copies a single file from a source dir into the package's assembly dir.
      At most one of dest_dir and dest_file should be supplied.
      If both are empty, then src_file is copied into the assembly dir.
  """

  def __init__(self, src_file, dest_dir=None, dest_file=None):
    step.Step.__init__(self)
    self.src_file = src_file
    self.dest_dir = dest_dir
    self.dest_file = dest_file

  def resolve(self, package):
    (dest_dir, dest_file, src_file) = self.resolve_filenames(package, False)
    package.resolved_input_file(src_file)


  def resolve_filenames(self, package, prepend_basedir=True):
    """ Return true (dest_dir, dest_file, src_file) tuple to use in the rule """

    prepend_dest_basedir = prepend_basedir
    prepend_src_basedir = prepend_basedir

    if self.dest_file != None and self.dest_dir != None:
      raise TargetError(package, "Error: CopyFile has both dest_dir and dest_file set")
    elif self.dest_file != None:
      if os.sep not in package.force(self.dest_file):
        # dest_file has no path component; put it directly in outdir.
        dest_dir = paths.OUTDIR_QUALIFIER
        prepend_dest_basedir = False
      else:
        # dest_file has a path component; use it.
        dest_dir = os.path.dirname(package.force(self.dest_file)) + os.sep
      dest_file = os.path.basename(package.force(self.dest_file))
    elif self.dest_dir != None:
      dest_dir = package.force(self.dest_dir)
      dest_file = package.force(self.dest_dir) # the 'where-to-copy' is just a dirname.
    else:
      dest_dir = paths.OUTDIR_QUALIFIER
      dest_file = paths.OUTDIR_QUALIFIER
      prepend_dest_basedir = False

    dest_dir = package.normalize_user_path(dest_dir, is_dest_path=True, \
        include_basedir=prepend_dest_basedir)
    dest_file = package.normalize_user_path(dest_file, is_dest_path=True, \
        include_basedir=prepend_dest_basedir)
    src_file = package.normalize_user_path(self.src_file, is_dest_path=False, \
        include_basedir=prepend_src_basedir)

    return (dest_dir, dest_file, src_file)


  def emitPackageOps(self, package):

    (dest_dir, dest_file, src_file) = self.resolve_filenames(package)

    text = """
  <mkdir dir="%(destdir)s" />
  <exec executable="rsync" failonerror="true">
    <arg value="--update" />
    <arg value="--copy-links" />
    <arg value="--perms" />
    <arg value="--times" />
    <arg value="%(srcfile)s" />
    <arg value="%(destfile)s" />
  </exec>
""" % { "destdir"  : dest_dir,
        "destfile" : dest_file,
        "srcfile"  : src_file }

    return text


class CopyDir(step.Step):
  """ Copies a source dir into the package's assembly dir """


  # static member.
  __permanent_excludes = set()

  @staticmethod
  def always_exclude(pattern):
    """ Defines a pattern which is always excluded in all CopyDir
        instances.

        This pattern is used as an argument to rsync --exclude.
        See the section "INCLUDE/EXCLUDE PATTERN RULES" of rsync(1)
        to see what's legal and how this is used.
    """
    CopyDir.__permanent_excludes.add(pattern)


  @staticmethod
  def clear_excludes_for_test():
    """ Used by unit tests to clear the always_exclude list; this should not
        be run in the production Targets files. Its effects are non-deterministic
        due to the non-deterministic order in which Targets files are consumed.
    """

    CopyDir.__permanent_excludes = set()


  @staticmethod
  def get_permanent_excludes():
    """ Returns the set of patterns set with always_exclude """
    return list(CopyDir.__permanent_excludes)


  def __init__(self, src_dir, dest_dir=None, exclude_patterns=None, force_refresh=False):
    step.Step.__init__(self)
    self.src_dir = src_dir
    self.dest_dir = dest_dir
    self.exclude_patterns = exclude_patterns
    self.force_refresh = force_refresh

  def resolve_dirs(self, package, prepend_basedir=True):
    if self.dest_dir == None:
      dest_dir = paths.OUTDIR_QUALIFIER
    else:
      dest_dir = package.force(self.dest_dir)

    dest_dir = package.normalize_user_path(dest_dir, is_dest_path=True, \
        include_basedir=prepend_basedir)
    src_dir = package.normalize_user_path(package.force(self.src_dir), is_dest_path=False, \
        include_basedir=prepend_basedir)

    if not src_dir.endswith(os.sep):
      src_dir = src_dir + os.sep

    return (dest_dir, src_dir)


  def resolve(self, package):
    (dest_dir, src_dir) = self.resolve_dirs(package, False)
    package.resolved_input_dir(src_dir)
    # TODO(aaron): Allow resolve_exclude to exclude input paths


  def emitPackageOps(self, package):

    (dest_dir, src_dir) = self.resolve_dirs(package)

    excludes_text = ""
    exclude_list = []
    exclude_list.extend(CopyDir.get_permanent_excludes())
    if self.exclude_patterns != None:
      exclude_list.extend(package.force(self.exclude_patterns))

    if exclude_list:
      for pattern in exclude_list:
        excludes_text = excludes_text + """
    <arg value="--exclude" />
    <arg value="%(pattern)s" />
""" % { "pattern" : pattern }

    if self.force_refresh:
      # We demand a new copy of this input every time, because a patch or
      # some other packaging action may modify it.
      update_mode = "delete"
    else:
      update_mode = "update"

    text = """
  <mkdir dir="%(destdir)s" />
  <exec executable="rsync" failonerror="true">
    <arg value="-r" />
    <arg value="--%(updatemode)s" />
    <arg value="--copy-links" />
    <arg value="--perms" />
    <arg value="--times" />
    %(excludes)s
    <arg value="%(srcdir)s" />
    <arg value="%(destdir)s" />
  </exec>
""" % { "srcdir"     : src_dir,
        "destdir"    : dest_dir,
        "updatemode" : update_mode,
        "excludes"   : excludes_text }

    return text


class Remove(step.Step):
  """ Removes files or directories from the filesystem.
      If recursive is False, assumes that 'name' is a file; otherwise,
      a directory.

      Care should be taken to ensure that you delete the path that
      you intend to; paths underneath the output dir should be prefixed with '$/'
  """

  def __init__(self, name, recursive=False):
    step.Step.__init__(self)
    self.name = name
    self.recursive = recursive

  def emitPackageOps(self, package):
    finalName = package.normalize_user_path(package.force(self.name), is_dest_path=True)
    if self.recursive:
      return "  <delete dir=\"" + finalName + "\" />\n"
    else:
      return "  <delete file=\"" + finalName + "\" />\n"


class MakeDir(step.Step):
  """ Runs equivalent of "mkdir -p" to create a dir named dirname """

  def __init__(self, dirname):
    self.dirname = dirname

  def emitPackageOps(self, package):
    return "  <mkdir dir=\"" \
        + package.normalize_user_path(package.force(self.dirname), is_dest_path=True) \
        + "\"/>\n"


class Link(step.Step):
  """
      Create a symlink named "link_name" to a file/dir named "target_name"
  """

  def __init__(self, target_name, link_name):
    step.Step.__init__(self)
    self.target_name = target_name
    self.link_name = link_name

  def emitPackageOps(self, package):
    return """
  <exec executable="ln" failonerror="true">
    <arg value="-s" />
    <arg value="--force" />
    <arg value="%(target)s" />
    <arg value="%(link)s" />
  </exec>
""" % { "target" : package.normalize_select_user_path(package.force(self.target_name)),
        "link"   : package.normalize_user_path(package.force(self.link_name), is_dest_path=True)
      }


class Move(step.Step):
  """
      Move a source file/dir to a destination.
  """

  def __init__(self, src, dest):
    step.Step.__init__(self)
    self.src = src
    self.dest = dest


  def resolve(self, package):
    src = package.normalize_user_path(package.force(self.src), \
        is_dest_path=False, include_basedir=False)
    if src.endswith(os.sep):
      package.resolved_input_dir(src)
    else:
      package.resolved_input_file(src)


  def emitPackageOps(self, package):
    return """
  <exec executable="mv" failonerror="true">
    <arg value="%(src)s" />
    <arg value="%(dest)s" />
  </exec>
""" % { "src"  : package.normalize_user_path(package.force(self.src)),
        "dest" : package.normalize_user_path(package.force(self.dest), is_dest_path=True)
      }


