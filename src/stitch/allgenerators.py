# (c) Copyright 2009 Cloudera, Inc.
#
# An aggregation module used by stitch to query the list of
# available generators dynamically, and list them for the user.
# If you want stitch's listGenerators() method to list your
# generator, include it here.

from stitch.antgenerator import AntGenerator
from stitch.buildgenerator import BuildGenerator
from stitch.eclipsegen import EclipseGenerator
from stitch.generator import *


