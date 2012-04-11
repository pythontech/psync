#=======================================================================
#       $Id: coll.py,v 1.2 2011/01/31 12:45:32 pythontech Exp $
#	Test FileCollection and WebFilerCollection
#=======================================================================
import unittest
import psync
from helpers import *

class GenericTestCollection(unittest.TestCase):
    def test_readdir(self):
        populate('b',
                 b='f:bar\n:T1', # To check timestamp
                 c='l:b', 
                 d=dict(e='f:foo\n'))
        self.assertEqual(dir2dict('b'),
                         {'b':'f:bar\n',
                          'c':'l:b',
                          'd':{'e':'f:foo\n'}})
        # Create file or web collection (determined by subclass)
        col = self.collection()
        # See how it behaves
        dir = col.readdir(())
        self.assertEqual(sorted(dir.keys()), ['b','c','d'])
        b = dir['b']
        self.assertEqual(b.type, 'f')
        self.assertTrue(type(b.vsn) in (int,float)) # Perl provides int mtime
        self.assertEqual(b.vsn, T1)
        self.assertEqual(sorted(b.meta.keys()), ['mode','mtime','size'])
        self.assertEqual(b.meta['size'], 4)
        c = dir['c']
        self.assertEqual(c.type, 'l')
        self.assertEqual(c.vsn, 'b')
        d = dir['d']
        self.assertEqual(d.type, 'd')
        self.assertEqual(d.vsn, None)
        self.assertEqual(d.meta['mode'] & 077755, 040755)

    def test_writefile(self):
        # writefile(path, content, meta) -> state
        populate('b')
        col = self.collection()
        state = col.writefile(('c',), 'cccc', {'mtime':T2})
        self.assertEqual(dir2dict('b',True),
                         {'c':'f:cccc:T2'})
        # FIXME check state

    def test_readfile(self):
        # readfile(path) -> content
        populate('b', c='f:abcdef')
        col = self.collection()
        content = col.readfile(('c',))
        self.assertEqual(content, 'abcdef')

    def test_readlink(self):
        # readlink(path) -> link
        populate('b',
                 c='l:./d',
                 d='f:linked-to')
        col = self.collection()
        link = col.readlink(('c',))
        self.assertEqual(link, './d')

    def test_writelink(self):
        # writelink(path, link) -> state
        populate('b')
        col = self.collection()
        state = col.writelink(('c',), '/etc/rubbish')
        self.assertEqual(dir2dict('b'),
                         {'c':'l:/etc/rubbish'})
        # FIXME check state

    def test_mkdir(self):
        # mkdir(path, meta) -> state
        populate('b')
        col = self.collection()
        col = col.mkdir(('c',), {})
        self.assertEqual(dir2dict('b'),
                         {'c':{}})
        # FIXME check state

    def test_remove(self):
        # remove(path)
        pass

class TestFileCollection(GenericTestCollection):
    def collection(self):
        return psync.FileCollection('b')

class TestWebFilerCollection(WebFilerTest,GenericTestCollection):
    def collection(self):
        return self.webfilerCollection()

# Stop main() running generic superclass
del GenericTestCollection

if __name__=='__main__':
    unittest.main()
