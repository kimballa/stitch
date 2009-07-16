" Vim syntax file
" Language:	Stitch targets files
" Maintainer: Aaron Kimball <aaron@cloudera.com>
" Updated: 2009-07-16
"
" Based on Neil Schemanauer's Python syntax highligher
" for vim 7.2. Neil is <nas@python.ca>
"
"     INSTALLATION INSTRUCTIONS
"  Put this file in ~/.vim/syntax/
"


" For version 5.x: Clear all syntax items
" For version 6.x: Quit when a syntax file was already loaded
if version < 600
  syntax clear
elseif exists("b:current_syntax")
  finish
endif

" Aaron added this section here to highlight typical names
" encountered in targets files.

" Targets
syn keyword pythonOperator JarTarget
syn keyword pythonOperator JavaTestTarget
syn keyword pythonOperator PythonTarget
syn keyword pythonOperator PythonTestTarget
syn keyword pythonOperator ThirdPartyAntTarget
syn keyword pythonOperator JavaTarget
syn keyword pythonOperator StepBasedTarget
syn keyword pythonOperator PackageTarget
syn keyword pythonOperator VerStringTarget
syn keyword pythonOperator PythonRedistTarget
syn keyword pythonOperator TestSetTarget
syn keyword pythonOperator MakefileTarget
syn keyword pythonOperator CupTarget
syn keyword pythonOperator JFlexTarget 
syn keyword pythonOperator ThriftTarget
syn keyword pythonOperator RawAntTarget
syn keyword pythonOperator ProjectList
syn keyword pythonOperator EmptyTarget
syn keyword pythonOperator RegisterProperty
syn keyword pythonOperator RsyncTarget

" Steps
syn keyword pythonBuiltin CopyFile
syn keyword pythonBuiltin CopyDir
syn keyword pythonBuiltin Move
syn keyword pythonBuiltin Link
syn keyword pythonBuiltin MakeDir
syn keyword pythonBuiltin IncludePackage
syn keyword pythonBuiltin IncludeOutput
syn keyword pythonBuiltin Remove
syn keyword pythonBuiltin RawAntXml
syn keyword pythonBuiltin Tar
syn keyword pythonBuiltin AntCall
syn keyword pythonBuiltin Exec
syn keyword pythonBuiltin RpmBuild
syn keyword pythonBuiltin AddDistUtilsDataFile
syn keyword pythonBuiltin AddDistUtilsDataDir

" Thunks
syn keyword pythonBuiltin CanonicalName
syn keyword pythonBuiltin AssemblyDir
syn keyword pythonBuiltin AssemblyTopDir
syn keyword pythonBuiltin SrcDir
syn keyword pythonBuiltin ClassPathElements 
syn keyword pythonBuiltin RequiredTargets
syn keyword pythonBuiltin Outputs
syn keyword pythonBuiltin Head
syn keyword pythonBuiltin ToList
syn keyword pythonBuiltin Concat

" Target parameters
syn keyword pythonStatement ant_target
syn keyword pythonStatement args
syn keyword pythonStatement arguments
syn keyword pythonStatement base_dir
syn keyword pythonStatement base_version
syn keyword pythonStatement build_file
syn keyword pythonStatement buildfile_name
syn keyword pythonStatement build_javac_options
syn keyword pythonStatement build_rule_name
syn keyword pythonStatement build_xml
syn keyword pythonStatement classpath_elements
syn keyword pythonStatement clean_first
syn keyword pythonStatement clean_rule
syn keyword pythonStatement clean_rule_name
syn keyword pythonStatement clean_target
syn keyword pythonStatement clean_xml
syn keyword pythonStatement compile_step
syn keyword pythonStatement components
syn keyword pythonStatement create_tarball
syn keyword pythonStatement cup_file
syn keyword pythonStatement data_paths
syn keyword pythonStatement debug_javac_options
syn keyword pythonStatement debug_options
syn keyword pythonStatement default_rule
syn keyword pythonStatement dest
syn keyword pythonStatement dest_dir
syn keyword pythonStatement dest_file
syn keyword pythonStatement dir
syn keyword pythonStatement dirname
syn keyword pythonStatement exclude_patterns
syn keyword pythonStatement exec_name
syn keyword pythonStatement executable
syn keyword pythonStatement expect_error
syn keyword pythonStatement expect_status
syn keyword pythonStatement expect_success
syn keyword pythonStatement fail_on_error
syn keyword pythonStatement filename
syn keyword pythonStatement flex_file
syn keyword pythonStatement force_build
syn keyword pythonStatement force_refresh
syn keyword pythonStatement hadoop_dir
syn keyword pythonStatement include_zip
syn keyword pythonStatement inputs
syn keyword pythonStatement install_dir
syn keyword pythonStatement jar_name
syn keyword pythonStatement java_class
syn keyword pythonStatement javac_options
syn keyword pythonStatement java_options
syn keyword pythonStatement languages
syn keyword pythonStatement link_name
syn keyword pythonStatement main_class_name
syn keyword pythonStatement main_jar_target
syn keyword pythonStatement main_module
syn keyword pythonStatement makefile_name
syn keyword pythonStatement make_options
syn keyword pythonStatement manifest_file
syn keyword pythonStatement md5sum
syn keyword pythonStatement name
syn keyword pythonStatement outputs
syn keyword pythonStatement output_source_root
syn keyword pythonStatement package_name
syn keyword pythonStatement parser
syn keyword pythonStatement patch_plan
syn keyword pythonStatement patch_version
syn keyword pythonStatement properties
syn keyword pythonStatement prop_name
syn keyword pythonStatement prop_val
syn keyword pythonStatement python_module
syn keyword pythonStatement recursive
syn keyword pythonStatement required_targets
syn keyword pythonStatement rpm_build_cmd
syn keyword pythonStatement rpm_release
syn keyword pythonStatement sources
syn keyword pythonStatement spec_file
syn keyword pythonStatement src
syn keyword pythonStatement src_dir
syn keyword pythonStatement src_file
syn keyword pythonStatement standalone
syn keyword pythonStatement standalone_exempt
syn keyword pythonStatement steps
syn keyword pythonStatement step_xml
syn keyword pythonStatement subthunk
syn keyword pythonStatement symbols
syn keyword pythonStatement target_name
syn keyword pythonStatement testcases
syn keyword pythonStatement test_rule
syn keyword pythonStatement test_rule_name
syn keyword pythonStatement test_set_name
syn keyword pythonStatement test_target
syn keyword pythonStatement testXml
syn keyword pythonStatement thrift_file
syn keyword pythonStatement thunks
syn keyword pythonStatement timeout
syn keyword pythonStatement use_dist_utils
syn keyword pythonStatement version


"
" From here below, it's all python.
"

syn keyword pythonStatement	break continue del
syn keyword pythonStatement	except exec finally
syn keyword pythonStatement	pass print raise
syn keyword pythonStatement	return try with
syn keyword pythonStatement	global assert
syn keyword pythonStatement	lambda yield
syn keyword pythonStatement	def class nextgroup=pythonFunction skipwhite
syn match   pythonFunction	"[a-zA-Z_][a-zA-Z0-9_]*" contained
syn keyword pythonRepeat	for while
syn keyword pythonConditional	if elif else
syn keyword pythonOperator	and in is not or
" AS will be a keyword in Python 3
syn keyword pythonPreCondit	import from as
syn match   pythonComment	"#.*$" contains=pythonTodo,@Spell
syn keyword pythonTodo		TODO FIXME XXX contained

" Decorators (new in Python 2.4)
syn match   pythonDecoratorName	"[[:alpha:]_][[:alnum:]_]*\%(\.[[:alpha:]_][[:alnum:]_]*\)*" contained
syn match   pythonDecorator	"@" display nextgroup=pythonDecoratorName skipwhite

" strings
syn region pythonString		matchgroup=Normal start=+[uU]\='+ end=+'+ skip=+\\\\\|\\'+ contains=pythonEscape,@Spell
syn region pythonString		matchgroup=Normal start=+[uU]\="+ end=+"+ skip=+\\\\\|\\"+ contains=pythonEscape,@Spell
syn region pythonString		matchgroup=Normal start=+[uU]\="""+ end=+"""+ contains=pythonEscape,@Spell
syn region pythonString		matchgroup=Normal start=+[uU]\='''+ end=+'''+ contains=pythonEscape,@Spell
syn region pythonRawString	matchgroup=Normal start=+[uU]\=[rR]'+ end=+'+ skip=+\\\\\|\\'+ contains=@Spell
syn region pythonRawString	matchgroup=Normal start=+[uU]\=[rR]"+ end=+"+ skip=+\\\\\|\\"+ contains=@Spell
syn region pythonRawString	matchgroup=Normal start=+[uU]\=[rR]"""+ end=+"""+ contains=@Spell
syn region pythonRawString	matchgroup=Normal start=+[uU]\=[rR]'''+ end=+'''+ contains=@Spell
syn match  pythonEscape		+\\[abfnrtv'"\\]+ contained
syn match  pythonEscape		"\\\o\{1,3}" contained
syn match  pythonEscape		"\\x\x\{2}" contained
syn match  pythonEscape		"\(\\u\x\{4}\|\\U\x\{8}\)" contained
syn match  pythonEscape		"\\$"

if exists("python_highlight_all")
  let python_highlight_numbers = 1
  let python_highlight_builtins = 1
  let python_highlight_exceptions = 1
  let python_highlight_space_errors = 1
endif

if exists("python_highlight_numbers")
  " numbers (including longs and complex)
  syn match   pythonNumber	"\<0x\x\+[Ll]\=\>"
  syn match   pythonNumber	"\<\d\+[LljJ]\=\>"
  syn match   pythonNumber	"\.\d\+\([eE][+-]\=\d\+\)\=[jJ]\=\>"
  syn match   pythonNumber	"\<\d\+\.\([eE][+-]\=\d\+\)\=[jJ]\=\>"
  syn match   pythonNumber	"\<\d\+\.\d\+\([eE][+-]\=\d\+\)\=[jJ]\=\>"
endif

if exists("python_highlight_builtins")
  " builtin functions, types and objects, not really part of the syntax
  syn keyword pythonBuiltin	True False bool enumerate set frozenset help
  syn keyword pythonBuiltin	reversed sorted sum
  syn keyword pythonBuiltin	Ellipsis None NotImplemented __import__ abs
  syn keyword pythonBuiltin	apply buffer callable chr classmethod cmp
  syn keyword pythonBuiltin	coerce compile complex delattr dict dir divmod
  syn keyword pythonBuiltin	eval execfile file filter float getattr globals
  syn keyword pythonBuiltin	hasattr hash hex id input int intern isinstance
  syn keyword pythonBuiltin	issubclass iter len list locals long map max
  syn keyword pythonBuiltin	min object oct open ord pow property range
  syn keyword pythonBuiltin	raw_input reduce reload repr round setattr
  syn keyword pythonBuiltin	slice staticmethod str super tuple type unichr
  syn keyword pythonBuiltin	unicode vars xrange zip
endif

if exists("python_highlight_exceptions")
  " builtin exceptions and warnings
  syn keyword pythonException	ArithmeticError AssertionError AttributeError
  syn keyword pythonException	DeprecationWarning EOFError EnvironmentError
  syn keyword pythonException	Exception FloatingPointError IOError
  syn keyword pythonException	ImportError IndentationError IndexError
  syn keyword pythonException	KeyError KeyboardInterrupt LookupError
  syn keyword pythonException	MemoryError NameError NotImplementedError
  syn keyword pythonException	OSError OverflowError OverflowWarning
  syn keyword pythonException	ReferenceError RuntimeError RuntimeWarning
  syn keyword pythonException	StandardError StopIteration SyntaxError
  syn keyword pythonException	SyntaxWarning SystemError SystemExit TabError
  syn keyword pythonException	TypeError UnboundLocalError UnicodeError
  syn keyword pythonException	UnicodeEncodeError UnicodeDecodeError
  syn keyword pythonException	UnicodeTranslateError
  syn keyword pythonException	UserWarning ValueError Warning WindowsError
  syn keyword pythonException	ZeroDivisionError
endif

if exists("python_highlight_space_errors")
  " trailing whitespace
  syn match   pythonSpaceError   display excludenl "\S\s\+$"ms=s+1
  " mixed tabs and spaces
  syn match   pythonSpaceError   display " \+\t"
  syn match   pythonSpaceError   display "\t\+ "
endif

" This is fast but code inside triple quoted strings screws it up. It
" is impossible to fix because the only way to know if you are inside a
" triple quoted string is to start from the beginning of the file. If
" you have a fast machine you can try uncommenting the "sync minlines"
" and commenting out the rest.
syn sync match pythonSync grouphere NONE "):$"
syn sync maxlines=200
"syn sync minlines=2000

if version >= 508 || !exists("did_python_syn_inits")
  if version <= 508
    let did_python_syn_inits = 1
    command -nargs=+ HiLink hi link <args>
  else
    command -nargs=+ HiLink hi def link <args>
  endif

  " The default methods for highlighting.  Can be overridden later
  HiLink pythonStatement	Statement
  HiLink pythonFunction		Function
  HiLink pythonDecoratorName	Function
  HiLink pythonConditional	Conditional
  HiLink pythonRepeat		Repeat
  HiLink pythonString		String
  HiLink pythonRawString	String
  HiLink pythonEscape		Special
  HiLink pythonOperator		Operator
  HiLink pythonPreCondit	PreCondit
  HiLink pythonComment		Comment
  HiLink pythonTodo		Todo
  HiLink pythonDecorator	Define
  if exists("python_highlight_numbers")
    HiLink pythonNumber	Number
  endif
  if exists("python_highlight_builtins")
    HiLink pythonBuiltin	Function
  endif
  if exists("python_highlight_exceptions")
    HiLink pythonException	Exception
  endif
  if exists("python_highlight_space_errors")
    HiLink pythonSpaceError	Error
  endif

  delcommand HiLink
endif

let b:current_syntax = "stitch"

