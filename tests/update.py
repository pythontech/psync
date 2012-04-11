#=======================================================================
#	$Id: update.py,v 1.2 2011/01/17 20:21:11 pythontech Exp $
#       Test update after sync
#=======================================================================
import unittest
import psync
from helpers import *

class TestUpdate(unittest.TestCase):
    def test_update(self):
        populate('a', aa='f:aa:T0',
                 bb='l:./aa',
                 cc=dict(dd='f:ddd:T1',
                         ee='f:eee:T2'))
        populate('b')
        a = psync.FileCollection('a')
        b = psync.FileCollection('b')
        repo = psync.DictRepo()
        sync = LogSync(repo, a, b)
        # Initial sync
        log = sync.run()
        self.assertEqual(dir2dict('a'), dir2dict('b'))
        self.assertEqual(sorted(log),
                         ['a-b aa',
                          'a-b bb',
                          'a-b cc',
                          'a-b cc/dd',
                          'a-b cc/ee'])
        self.assertEqual(repo.as_data(),
                         {'aa':('f',T0,T0),
                          'bb':('l','./aa','./aa'),
                          'cc':{'dd':('f',T1,T1),
                                'ee':('f',T2,T2),
                                },
                          })
        # Now modify both sides
        repopulate('a', ff='f:f2:T1')
        repopulate('b', gg='f:g2:T1')
        os.remove('a/aa')
        log = sync.run()
        self.assertEqual(sorted(log),
                         ['a-b ff',
                          'b-a gg',
                          'del-b aa'])
        ad = dir2dict('a',True)
        bd = dir2dict('b',True)
        self.assertEqual(ad, bd)
        self.assertEqual(ad,{'bb':'l:./aa',
                             'cc':{'dd':'f:ddd:T1', 'ee':'f:eee:T2'},
                             'ff':'f:f2:T1',
                             'gg':'f:g2:T1'})
        self.assertEqual(repo.as_data(),
                         {'bb':('l','./aa','./aa'),
                          'cc':{'dd':('f',T1,T1),
                                'ee':('f',T2,T2),
                                },
                          'ff':('f',T1,T1),
                          'gg':('f',T1,T1),})
        # Remove file on both sides
        os.remove('a/ff')
        os.remove('b/ff')
        log = sync.run()
        self.assertEqual(sorted(log),
                         ['gone ff'])
        ad = dir2dict('a',True)
        bd = dir2dict('b',True)
        self.assertEqual(ad, bd)
        self.assertEqual(ad,{'bb':'l:./aa',
                             'cc':{'dd':'f:ddd:T1', 'ee':'f:eee:T2'},
                             'gg':'f:g2:T1'})
        self.assertEqual(repo.as_data(),
                         {'bb':('l','./aa','./aa'),
                          'cc':{'dd':('f',T1,T1),
                                'ee':('f',T2,T2),
                                },
                          'gg':('f',T1,T1),})

class LogSync(psync.Sync):
    def run(self):
        self.log = []
        psync.Sync.run(self)
        return self.log

    def conflict(self, path, astate, bstate):
        self.log.append('conflict %s' % '/'.join(path))

    def a_to_b(self, path, astate, bstate):
        fn = '/'.join(path)
        if astate:
            self.log.append('a-b %s' % fn)
        else:
            self.log.append('del-b %s' % fn)
        psync.Sync.a_to_b(self, path, astate, bstate)

    def b_to_a(self, path, astate, bstate):
        fn = '/'.join(path)
        if bstate:
            self.log.append('b-a %s' % fn)
        else:
            self.log.append('del-a %s' % fn)
        psync.Sync.b_to_a(self, path, astate, bstate)

    def both_gone(self, path):
        self.log.append('gone %s' % '/'.join(path))
        try:
            psync.Sync.both_gone(self, path)
        except: pass

if __name__=='__main__':
    unittest.main()
