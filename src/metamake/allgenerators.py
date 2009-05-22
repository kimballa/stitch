# (c) Copyright 2009 Cloudera, Inc.
#
# An aggregation module used by metamake to query the list of
# available generators dynamically, and list them for the user.
# If you want metamake's listGenerators() method to list your
# generator, include it here.

from metamake.antgenerator import AntGenerator
from metamake.buildgenerator import BuildGenerator
from metamake.eclipsegen import EclipseGenerator
from metamake.generator import *


