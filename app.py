#=======================================================================
#       Command-line application
#=======================================================================
import ConfigParser
import psync
import sys
import os
import logging

class CmdError(Exception): pass
class UsageError(Exception): pass

class PsyncApp:
    def __init__(self):
        self.syncs = {}         # name -> Sync

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
        op = OptionParser('%prog [options] method [arg..]')
        op.add_option('--config','-c',
                      help='alternative to ~/.psync')
        op.add_option('--debug','-d',
                      action='store_true',
                      help='Debug logging')
        if argv is not None:
            op.prog = argv[0]
            argv = argv[1:]
        opts, args = op.parse_args(argv)
        if opts.debug:
            logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
        inifile = opts.config
        if inifile is None:
            inifile = os.path.expanduser('~/.psync')
        self.read_inifile(inifile)
        # Process arguments
        if len(args) < 1:
            op.error('No command')
        else:
            try:
                self.do_cmd(args[0], args[1:], opts)
            except UsageError, e:
                op.error('Error in %s command: %s' % (args[0], e.args[0]))
            except CmdError, e:
                op.error(e.args[0])

    def do_cmd(self, cmd, args, opts):
        if cmd == 'list':
            for name in sorted(self.syncs.keys()):
                print name
        else:
            # Other commands need a Sync
            if len(args) < 1:
                raise UsageError('no sync specified')
            syncname = args.pop(0)
            if not syncname in self.syncs:
                raise CommandError('unknown sync %r' % syncname)
            sync = self.syncs[syncname]
            if cmd == 'show':
                if args:
                    raise UsageError('excess arguments')
                print 'a', sync.a
                print 'b', sync.b
            elif cmd == 'status':
                if not args:
                    raise UsageError('missing path')
                if len(args) > 1:
                    raise UsageError('excess arguments')
                spath = args.pop(0)
                if not spath:
                    path = []
                else:
                    path = spath.split('/')
                state = sync.repo.getstate(path)
                print state
            elif cmd == 'scan':
                if len(args) > 0:
                    raise UsageError('excess arguments')
                sync.run()
            else:
                raise CmdError('Unknown/unimplemented command %r' % cmd)

def make_repo(repodef):
    '''Convert "class:path" string into Repo instance'''
    cls, path = repodef.split(':', 1)
    if cls == 'shelve':
        return psync.ShelveRepo(os.path.expanduser(path))
    elif cls == 'sqlite':
        import sqlrepo
        return sqlrepo.SqlRepo(os.path.expanduser(path))
    else:
        raise ValueError, 'Unknown repo type %r' % cls

def make_coll(colldef):
    '''Convert "class:path" string into Collection instance'''
    cls, path = colldef.split(':', 1)
    if cls == 'file':
        return psync.FileCollection(os.path.expanduser(path))
    else:
        raise ValueError, 'Unknown collection type %r' % cls

if __name__=='__main__':
    PsyncApp().cmdline()
