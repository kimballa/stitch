# (c) Copyright 2009 Cloudera, Inc.
#
# An aggregation module used by metamake to query the list of
# available generators dynamically, and list them for the user.
# If you want metamake's listGenerators() method to list your
# generator, include it here.

from metamakelib.antgenerator import AntGenerator
from metamakelib.buildgenerator import BuildGenerator
from metamakelib.eclipsegen import EclipseGenerator
from metamakelib.generator import *


