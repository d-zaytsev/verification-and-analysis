# Statements without control flow must land in the basic block as is.
import os
from sys import argv as args

global counter
counter = len(args)
type Path = str | os.PathLike[str]
del args
print(counter)
