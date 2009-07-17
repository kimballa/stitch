# (c) Copyright 2009 Cloudera, Inc.
#
# ctarget.py
#
# Defines the CCTarget and CxxTarget classes for compiling to .o files,
# the Executable target to link an executable, and the Library target
# that links a library.
#
# This makes use of the ant-contrib cpptasks library.

import os

import stitch.paths as paths
from   stitch.targets.targeterror import TargetError
from   stitch.targets.target import *
from   stitch.targets.anttarget import *
import stitch.antgenerator as antgenerator



class CCBaseTarget(AntTarget):
  """ Abstract class used to control a gcc-like compiler. """
  
  # enum for how CCBaseTarget should act
  OBJ_ONLY    = 0 # Just compile to .o files
  EXECUTABLE  = 1 # Build a user-runnable executable.
  DYNAMIC_LIB = 2 # Build a .so library.
  STATIC_LIB  = 3 # build a .a library.

  def __init__(self, sources, cflags, include_dirs, lib_dirs, libs, required_targets,
               compiler, debug_info, build_type, output_name, optimize, exts):
    AntTarget.__init__(self)
    self.sources = sources
    self.cflags = cflags
    self.include_dirs = include_dirs
    self.lib_dirs = lib_dirs
    self.libs = libs
    self.required_targets = required_targets
    self.compiler = compiler
    self.debug_info = debug_info
    self.build_type = build_type
    self.output_name = output_name
    self.optimize = optimize
    self.exts = exts


  def get_sources(self):
    return self.force(self.sources)


  def language(self):
    return "C"

  # Methods allowing C-generating targets to inform one another what
  # sort of dependencies they generate.
  def generates_c_source(self):
    return False

  def generates_c_headers(self):
    return False

  def generates_c_objects(self):
    return self.build_type == CCBaseTarget.OBJ_ONLY

  def generates_c_library(self):
    return self.build_type == CCBaseTarget.DYNAMIC_LIB \
        or self.build_type == CCBaseTarget.STATIC_LIB

  def get_ant_rule_map(self):
    return {
      "build"   : self.getSafeName() + "-build",
      "default" : self.getSafeName() + "-build",
      "clean"   : self.getSafeName() + "-clean",
    }


  def cleanRule(self, rule):
    """ generate a clean command """

    (mainName, ruleType) = self.splitRuleName(rule)

    text = "<target name=\"" + rule + "\">\n"
    dest_dir = self.get_assembly_dir()
    text = text + "  <deletermf dir=\"" + dest_dir + "\" />\n"
    text = text + "</target>\n"
    return text

  def __lib_text(self, lib_dirs, libs, is_for_linker=False):
    """ Generate the -L and -l arguments to pass to gcc """
    text = ""

    if is_for_linker:
      argtype = "linkerarg"
    else:
      argtype = "compilerarg"

    # Process library directories.
    for dir in lib_dirs:
      text = text + "    <" + argtype + " value=\"-L" + dir + "\" />\n"

    # Include any libraries we depend on.
    for lib in libs:
      text = text + "    <" + argtype + " value=\"-l" + lib + "\" />\n"

    return text


  def buildRule(self, rule):
    """ Generate a build command """

    (mainName, ruleType) = self.splitRuleName(rule)

    text = "<target name=\"" + rule + "\" "
    depAntRules = self.getAntDependencies(ruleType)
    text = text + depAntRules + ">\n"

    dest_dir = self.get_assembly_dir()
    text = text + "  <mkdir dir=\"" + dest_dir + "\" />\n"

    text = text + "  <cc name=\"" + self.compiler + "\" debug=\"" \
        + str(self.debug_info).lower() + "\" "
    text = text + "optimize=\"" + str(self.optimize).lower() + "\" "
    if self.build_type == CCBaseTarget.OBJ_ONLY:
      text = text + "objdir=\"" + dest_dir + "\""
    elif self.build_type == CCBaseTarget.EXECUTABLE:
      text = text + "outtype=\"executable\" "
      text = text + "outfile=\"" + dest_dir + os.sep + self.output_name + "\" "
    elif self.build_type == CCBaseTarget.DYNAMIC_LIB:
      text = text + "outtype=\"shared\" "
      text = text + "outfile=\"" + dest_dir + os.sep + self.output_name + "\" "
    elif self.build_type == CCBaseTarget.STATIC_LIB:
      text = text + "outtype=\"static\" "
      text = text + "outfile=\"" + dest_dir + os.sep + self.output_name + "\" "
    text = text + ">\n"

    if self.cflags != None:
      for flag in self.cflags:
        text = text + "    <compilerarg value=\"" + flag + "\" />\n"

    # Force thunks.
    lib_dirs = self.force(self.lib_dirs)
    include_dirs = self.force(self.include_dirs)
    sources = self.force(self.sources)
    libs = self.force(self.libs)

    if lib_dirs == None:
      lib_dirs = []
    if include_dirs == None:
      include_dirs = []
    if sources == None:
      sources = []
    if libs == None:
      libs = []
    objs = []

    # Process any incoming dependencies.
    # This could either be libraries that we need to include via -l,
    # directories full of source we need to compile with a <fileset>,
    # directories full of compiled output,
    # or directories full of headers we need to include via -I.
    if self.required_targets != None:
      for target in self.required_targets:
        targetObj = self.getTargetByName(target)
        if targetObj.language() == "C":
          if targetObj.generates_c_source():
            sources.extend(targetObj.intermediatePaths())
          if targetObj.generates_c_headers():
            include_dirs.extend(targetObj.intermediatePaths())
          if targetObj.generates_c_objects():
            objs.extend(targetObj.outputPaths())
          if targetObj.generates_c_library():
            libs.extend(targetObj.outputPaths())
          
    if self.compiler == "g++":
      # cpptasks only uses gcc for the linker, not g++, so we must
      # enforce linking against c++.
      libs.append("stdc++")
    
    # Process include dirs.
    for dir in include_dirs:
      text = text + "    <includepath path=\"" + dir + "\" />\n"
      
    # This is the directory containing the targets file. User-specified sources assumed below here.
    source_root = os.path.join("${basedir}", self.getInputDirectory())

    # Include all the source files to compile.
    for src in sources:
      src = self.normalize_user_path(src)
      if src.endswith(os.sep):
        # it's a directory source.
        text = text + "    <fileset dir=\"" + src + "\">\n"
        for ext in self.exts:
          text = text + "      <include name=\"**/*." + ext + "\" />\n"
        text = text + "    </fileset>\n"
      else:
        # it's just a single file.
        text = text + "    <fileset file=\"" + src + "\" />\n"

    for objpath in objs:
      # These are paths to dirs full of .o files added by required_targets.
      text = text + "    <fileset dir=\"" + objpath + "\">\n"
      text = text + "      <include name=\"**/*.o\" />\n"
      text = text + "    </fileset>\n"

    text = text + self.__lib_text(lib_dirs, libs, is_for_linker=False)

    if self.build_type != CCBaseTarget.OBJ_ONLY:
      # We'll be doing linking; specify the linker executable name too.
      text = text + "    <linker name=\"" + self.compiler + "\">\n"
      text = text + self.__lib_text(lib_dirs, libs, is_for_linker=True)
      text = text + "    </linker>\n"

    text = text + "  </cc>\n"
    text = text + "</target>\n"
    return text


  def antRule(self, rule):
    (mainName, ruleType) = self.splitRuleName(rule)

    if ruleType == "clean":
      return self.cleanRule(rule)
    elif ruleType == "build":
      return self.buildRule(rule)


  def outputPaths(self):
    if self.build_type == CCBaseTarget.OBJ_ONLY:
      # We're just creating a set of .o files. Return the dir.
      return [ self.get_assembly_dir() ]
    elif self.build_type == CCBaseTarget.EXECUTABLE:
      # We're creating a program with the same name as the one the user specifie.d
      return [ self.get_assembly_dir() + os.sep + output_name ]
    elif self.build_type == CCBaseTarget.DYNAMIC_LIB:
      # We're creating a dynamic library.
      return [ self.get_assembly_dir() + os.sep + "lib" + output_name + ".so" ]
    elif self.build_type == CCBaseTarget.STATIC_LIB:
      # We're creating a static library.
      return [ self.get_assembly_dir() + os.sep + "lib" + output_name + ".a" ]


class CCTarget(CCBaseTarget):
  """ Invokes a C compiler on the provided sources to make .o files

      Parameters:

      sources           req   List of files or directories to compile.
      cflags            opt   List of arguments to pass to the compiler
      include_dirs      opt   List of directories to reference with -I
      lib_dirs          opt   List of directories to reference with -L
      libs              opt   List of libraries to link with, via -l
      required_targets  opt   (The usual)
      compiler          opt   Executable of the compiler (default=gcc)
      debug_info        opt   boolean, default false. Generate debug info?
      optimize          opt   "none", "speed", or "size". default none.
      extensions        opt   List of file extensions to process. default=["c"]
  """

  def __init__(self, sources, cflags=None, include_dirs=None, lib_dirs=None,
               libs=None, required_targets=None, compiler="gcc", debug_info=False,
               optimize="none", extensions=None):
    if extensions == None:
      extensions = [ "c" ]
    CCBaseTarget.__init__(self, sources, cflags, include_dirs, lib_dirs, libs,
        required_targets, compiler, debug_info, CCBaseTarget.OBJ_ONLY, None, optimize,
        extensions)


class CxxTarget(CCBaseTarget):
  """ All this class does differently from CCTarget is set compiler=g++. """
  def __init__(self, sources, cflags=None, include_dirs=None, lib_dirs=None,
               libs=None, required_targets=None, compiler="g++", debug_info=False,
               optimize="none", extensions=None):
    if extensions == None:
      extensions = [ "C", "cpp", "cxx" ]
    CCBaseTarget.__init__(self, sources, cflags, include_dirs, lib_dirs, libs,
        required_targets, compiler, debug_info, CCBaseTarget.OBJ_ONLY, None, optimize,
        extensions)


class Executable(CCBaseTarget):
  """ Invokes the linker to generate an executable.

      If sources isn't given, then required_targets must be.

      Parameters

      name              req   Name of the executable to generate.
      sources           opt   List of files or directories to compile.
      cflags            opt   List of arguments to pass to the compiler
      include_dirs      opt   List of directories to reference with -I
      lib_dirs          opt   List of directories to reference with -L
      libs              opt   List of libraries to link with, via -l
      required_targets  opt   (The usual)
      compiler          opt   Executable of the compiler (default=gcc)
      debug_info        opt   boolean, default false. Generate debug info?
      optimize          opt   boolean, default false. Run with -O?
      extensions        opt   List of file extensions to process. default=["c"]
  """

  def __init__(self, name, sources=None, cflags=None, include_dirs=None, lib_dirs=None,
               libs=None, required_targets=None, compiler="gcc", debug_info=False,
               optimize="none", extensions=None):
    if extensions == None:
      extensions = [ "c" ]
    CCBaseTarget.__init__(self, sources, cflags, include_dirs, lib_dirs, libs, required_targets,
      compiler, debug_info, CCBaseTarget.EXECUTABLE, name, optimize, extensions)
  

class Library(CCBaseTarget):
  """ Invokes the linker to generate a shared library.

      If sources isn't given, then required_targets must be.

      Parameters

      name              req   Name of the library to generate.
      dynamic           opt   Boolean, default true. If false, generates a static lib.
      sources           opt   List of files or directories to compile.
      cflags            opt   List of arguments to pass to the compiler
      include_dirs      opt   List of directories to reference with -I
      lib_dirs          opt   List of directories to reference with -L
      libs              opt   List of libraries to link with, via -l
      required_targets  opt   (The usual)
      compiler          opt   Executable of the compiler (default=gcc)
      debug_info        opt   boolean, default false. Generate debug info?
      optimize          opt   boolean, default false. Run with -O?
      extensions        opt   List of file extensions to process. default=["c"]
  """

  def __init__(self, name, dynamic=True, sources=None, cflags=None, include_dirs=None,
               lib_dirs=None, libs=None, required_targets=None, compiler="gcc", debug_info=False,
               optimize="none", extensions=None):
    if dynamic:
      type = CCBaseTarget.DYNAMIC_LIB
    else:
      type = CCBaseTarget.STATIC_LIB
    if extensions == None:
      extensions = [ "c" ]
      
    CCBaseTarget.__init__(self, sources, cflags, include_dirs, lib_dirs, libs, required_targets,
        compiler, debug_info, type, name, optimize, extensions)

