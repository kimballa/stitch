
from stitch.targets.alltargets import *

def EchoTarget(msg):
  """ Returns a StepBasedTarget that echos a message """
  return StepBasedTarget(
    steps = [
      Exec(
        executable="echo",
        arguments = [ msg ])],
    clean_first = True)

