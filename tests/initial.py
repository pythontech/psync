#=======================================================================
#	$Id: initial.py,v 1.2 2011/01/17 20:18:50 pythontech Exp $
#       Test initial sync (no previous state)
#=======================================================================
import unittest
import psync
from helpers import *

class TestInitial(unittest.TestCase):
    def test_merge(self):
        populate('a', aa='f:aa:T0')
        populate('b', bb='f:bb:T1',
                 cc='l:./bb',
                 dd=dict(ee='f:eee:T2'))
        a = psync.FileCollection('a')
        b = psync.FileCollection('b')
        repo = psync.DictRepo()
        sync = psync.Sync(repo, a, b)
        sync.run()
        # Should copy aa from a to b, bb from b to a
        self.assertEqual(dir2dict('a',True),
                         {'aa':'f:aa:T0', 'bb':'f:bb:T1', 'cc':'l:./bb',
                          'dd':{'ee':'f:eee:T2'}})
        self.assertEqual(dir2dict('a'), dir2dict('b'))
        self.assertEqual(mtime('a/dd/ee'), T2)
        self.assertEqual(repo.as_data(),
                         {'aa':('f',T0,T0),
                          'bb':('f',T1,T1),
                          'cc':('l','./bb','./bb'),
                          'dd':{'ee':('f',T2,T2)}})

    def test_later(self):
        # Same path with different content and modtime - conflict
        populate('a', aa='f:a0:T0')
        populate('b', aa='f:a11:T1')
        a = psync.FileCollection('a')
        b = psync.FileCollection('b')
        repo = psync.DictRepo()
        sync = TestSync(repo, a, b)
        confs = sync.testsync()
        self.assertEqual(confs, [(('aa',), ('f',T0), ('f',T1))])
        self.assertEqual(dir2dict('a',True),
                         {'aa':'f:a0:T0'})
        self.assertEqual(dir2dict('b',True),
                         {'aa':'f:a11:T1'})

class TestSync(psync.Sync):
    def __init__(self, *args, **kw):
        psync.Sync.__init__(self, *args, **kw)
        self.conflicts = []
    def conflict(self, path, astate, bstate):
        self.conflicts.append((path, 
                               (astate.type, astate.vsn),
                               (bstate.type, bstate.vsn)))
    def testsync(self):
        self.run()
        return self.conflicts

if __name__=='__main__':
    unittest.main()
