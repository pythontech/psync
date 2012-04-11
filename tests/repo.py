#=======================================================================
#	$Id: repo.py,v 1.1 2011/01/05 19:59:12 pythontech Exp $
#       Test repository
#=======================================================================
import unittest
import psync
from helpers import *

class TestEmpty(unittest.TestCase):
    def test_empty(self):
        repo = psync.DictRepo()
        p0 = ['ab']
        p1 = ['ab','cd']
        self.assertEqual(repo.getstate(p1), None)
        repo.setstate(p1, 'f',12,34)
        #print sorted(repo.store.keys())
        s = repo.getstate(p1)
        self.assertEqual(s.type, 'f')
        self.assertEqual(s.avsn, 12)
        self.assertEqual(s.bvsn, 34)
        self.assertEqual(repo.store,
                         {'d0':(1,),
                          'd1':(2,),
                          'i0,ab':1,
                          'i1,cd':2,
                          'l':2,
                          'n1':'ab',
                          'n2':'cd',
                          'p1':0,
                          'p2':1,
                          's2':('f', 12, 34)})
        self.assertEqual(repo.as_data(),
                         {'ab':{'cd':('f',12,34)}})

    def test_del(self):
        repo = psync.DictRepo()
        repo.setstate(['ab','cd'], 'f',12,34)
        repo.delstate(['ab','cd'])
        self.assertEqual(repo.as_data(), {'ab':{}})
        repo.delstate(['ab'])
        self.assertEqual(repo.as_data(), {})

class TestShelve(unittest.TestCase):
    def test_shelve(self):
        repo = psync.ShelveRepo('tsh')
        repo.setstate(['abc'], 'f',123,456)
        repo.flush()
        self.assertEqual(dict(repo.store),
                         {'l':1,
                          'd0':(1,),
                          'i0,abc':1,
                          'p1':0,
                          'n1':'abc',
                          's1':('f',123,456)})

if __name__=='__main__':
    unittest.main()
