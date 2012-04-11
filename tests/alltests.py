import sys
import os.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import unittest
from repo import *
from initial import *
from update import *
from coll import *

unittest.main()
