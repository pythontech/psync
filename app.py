import ConfigParser
import psync
import os

class PsyncApp:
    def __init__(self):
        self.syncs = {}

    def read_inifile(self, inifile):
        cp = ConfigParser.SafeConfigParser()
        cp.read(inifile)
        for section in cp.sections():
            repo = make_repo(cp.get(section, 'repo'))
            acoll = make_coll(cp.get(section, 'a'))
            bcoll = make_coll(cp.get(section, 'b'))
            sync = psync.Sync(repo, acoll, bcoll)
            self.syncs[section] = sync

    def cmdline(self, argv=None):
        '''Supported commands:
        psync list
        psync show <sync>
        psync a <sync> <path>...
        psync b <sync> <path>...
        '''
        from optparse import OptionParser
        op = OptionParser()
        op.add_option('--config','-c',
                      help='alternative to ~/.psync')
        if argv is not None:
            op.prog = argv[0]
            argv = argv[1:]
        opts, args = op.parse_args(argv)
        inifile = opts.config
        if inifile is None:
            inifile = os.path.expanduser('~/.psync')
        self.read_inifile(inifile)
        # Process arguments
        if len(args) < 1:
            op.error('No command')
        cmd = args.pop(0)
        if cmd == 'list':
            for name in sorted(self.syncs.keys()):
                print name
        else:
            self.error('Unknown/unimplemented command %r' % cmd)

def make_repo(repodef):
    cls, path = repodef.split(':', 2)
    if cls == 'shelve':
        return psync.ShelveRepo(os.path.expanduser(path))
    elif cls == 'sqlite':
        import sqlrepo
        return sqlrepo.SqlRepo(os.path.expanduser(path))
    else:
        raise ValueError, 'Unknown repo type %r' % cls

def make_coll(colldef):
    cls, path = colldef.split(':', 2)
    if cls == 'file':
        return psync.FileCollection(os.path.expanduser(path))
    else:
        raise ValueError, 'Unknown collection type %r' % cls

if __name__=='__main__':
    PsyncApp().cmdline()
