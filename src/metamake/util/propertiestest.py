# (c) Copyright 2009 Cloudera, Inc.
#
# Unit test cases for Properties
#
# @author aaron

from metamake.testutil.asserts import TestCaseWithAsserts

from properties import Properties

class LineBuffer(object):
  """ Allows you to store a bunch of lines of text in an object;
      the readlines() method will return all of them and clear the
      buffer. Used as a helper method in this set of tests. """

  def __init__(self):
    self.lines = []

  def append(self, line):
    self.lines.append(line)

  def close(self):
    pass

  def readlines(self):
    ret = self.lines
    self.lines = []
    return ret

class PropertiesTest(TestCaseWithAsserts):

  def testBasic1(self):
    lb = LineBuffer()
    lb.append("x = 42\n")
    dict = { "x" : "42" }
    p = Properties()
    p.load(lb)
    self.assertTrue(p.equalsDict(dict))

  def testBasic2(self):
    lb = LineBuffer()
    lb.append("x : 42\n")
    dict = { "x" : "42" }
    p = Properties()
    p.load(lb)
    self.assertTrue(p.equalsDict(dict))

  def testBasic3(self):
    lb = LineBuffer()
    lb.append("x 42\n")
    dict = { "x" : "42" }
    p = Properties()
    p.load(lb)
    self.assertTrue(p.equalsDict(dict))

  def testWhitespace1(self):
    lb = LineBuffer()
    lb.append("x =      42\n")
    dict = { "x" : "42" }
    p = Properties()
    p.load(lb)
    self.assertTrue(p.equalsDict(dict))

  def testWhitespace2(self):
    lb = LineBuffer()
    lb.append("x       =  42\n")
    dict = { "x" : "42" }
    p = Properties()
    p.load(lb)
    self.assertTrue(p.equalsDict(dict))

  def testWhitespace3(self):
    lb = LineBuffer()
    lb.append("x=42\n")
    dict = { "x" : "42" }
    p = Properties()
    p.load(lb)
    self.assertTrue(p.equalsDict(dict))

  def testWhitespace4(self):
    lb = LineBuffer()
    lb.append("x=4\\\n")
    lb.append("2\n")
    dict = { "x" : "42" }
    p = Properties()
    p.load(lb)
    self.assertTrue(p.equalsDict(dict))

  def testWhitespace4(self):
    lb = LineBuffer()
    lb.append("x=\\\n")
    lb.append("42\n")
    dict = { "x" : "42" }
    p = Properties()
    p.load(lb)
    self.assertTrue(p.equalsDict(dict))

  def testEscape1(self):
    lb = LineBuffer()
    lb.append("x=4\\t2\n")
    dict = { "x" : "4\t2" }
    p = Properties()
    p.load(lb)
    self.assertTrue(p.equalsDict(dict))

  def testRawTab(self):
    lb = LineBuffer()
    lb.append("x=4\t2\n")
    dict = { "x" : "4\t2" }
    p = Properties()
    p.load(lb)
    self.assertTrue(p.equalsDict(dict))

  def testEscape2(self):
    lb = LineBuffer()
    lb.append("x=4\\z2\n")
    dict = { "x" : "4z2" }
    p = Properties()
    p.load(lb)
    self.assertTrue(p.equalsDict(dict))

  def testEscape3(self):
    lb = LineBuffer()
    lb.append("x=4\\\\2\n")
    dict = { "x" : "4\\2" }
    p = Properties()
    p.load(lb)
    self.assertTrue(p.equalsDict(dict))

  def testEscape4(self):
    lb = LineBuffer()
    lb.append("x=4\\\\\\\\\\2\n")
    dict = { "x" : "4\\\\2" }
    p = Properties()
    p.load(lb)
    self.assertTrue(p.equalsDict(dict))

  def testKeyEscape1(self):
    lb = LineBuffer()
    lb.append("x\\=y=42\n")
    dict = { "x=y" : "42" }
    p = Properties()
    p.load(lb)
    self.assertTrue(p.equalsDict(dict))

  def testKeyEscape2(self):
    lb = LineBuffer()
    lb.append("x\\ y=42\n")
    dict = { "x y" : "42" }
    p = Properties()
    p.load(lb)
    self.assertTrue(p.equalsDict(dict))

  def testOverwrite(self):
    lb = LineBuffer()
    lb.append("x=42\n")
    lb.append("x=44\n")
    dict = { "x" : "44" }
    p = Properties()
    p.load(lb)
    self.assertTrue(p.equalsDict(dict))

  def testIgnoreComments(self):
    lb = LineBuffer()
    lb.append("# this is a comment\n")
    lb.append("x=42\n")
    lb.append("! this is also a comment\n")
    lb.append("    # comment\n")
    dict = { "x" : "42" }
    p = Properties()
    p.load(lb)
    self.assertTrue(p.equalsDict(dict))

  def testIgnoreBlanks(self):
    lb = LineBuffer()
    lb.append("\n")
    lb.append("x=42\n")
    lb.append("                 \n")
    lb.append("    # comment\n")
    dict = { "x" : "42" }
    p = Properties()
    p.load(lb)
    self.assertTrue(p.equalsDict(dict))

  def testTrailingSpace(self):
    lb = LineBuffer()
    lb.append("x=42   \n")
    dict = { "x" : "42   " }
    p = Properties()
    p.load(lb)
    self.assertTrue(p.equalsDict(dict))

  def testLineContinue(self):
    lb = LineBuffer()
    lb.append("x=42   \\\n")
    lb.append("        boo\n")
    dict = { "x" : "42   boo" }
    p = Properties()
    p.load(lb)
    self.assertTrue(p.equalsDict(dict))

  def testEmptyProperty1(self):
    lb = LineBuffer()
    lb.append("x\n")
    dict = { "x" : "" }
    p = Properties()
    p.load(lb)
    self.assertTrue(p.equalsDict(dict))

  def testEmptyProperty2(self):
    lb = LineBuffer()
    lb.append("x:\n")
    dict = { "x" : "" }
    p = Properties()
    p.load(lb)
    self.assertTrue(p.equalsDict(dict))

  def testEmptyProperty3(self):
    lb = LineBuffer()
    lb.append("x=       \n")
    dict = { "x" : "" }
    p = Properties()
    p.load(lb)
    self.assertTrue(p.equalsDict(dict))

  def testNoLineContinue(self):
    lb = LineBuffer()
    lb.append("x=42   \\  \n")
    lb.append("        boo\n")
    dict = { "x" : "42     ", \
             "boo" : "" }
    p = Properties()
    p.load(lb)
    self.assertTrue(p.equalsDict(dict))


if __name__ == '__main__':
  unittest.main()


