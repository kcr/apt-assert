#!/usr/bin/python

import sys, os, shlex, logging, optparse, itertools, re
import apt

class InstalledFilter(apt.cache.Filter):
    """ Filter that returns the currently installed packages """

    def apply(self, pkg):
        return bool(pkg.installed)

class UpgradableFilter(InstalledFilter):
    """ Filter that returns installed, upgradable packagess """

    def apply(self, pkg):
        return super(UpgradableFilter, self).apply(pkg) and  pkg.installed < pkg.candidate

class LogFetchProgress(apt.progress.FetchProgress):
    """ progress object for logger;  adapted from apt.progress.TextFetchProgress """

    def __init__(self, log):
        super(LogFetchProgress, self).__init__()
        self.log = log

    def updateStatus(self, uri, descr, shortDescr, status):
        """Called when the status of an item changes.

        This happens eg. when the downloads fails or is completed.
        """
        if status != self.dlQueued:
            self.log.info("%s %s", self.dlStatusStr[status], descr)

    def stop(self):
        """Called when all files have been fetched."""
        self.log.info('Done downloading')

    def mediaChange(self, medium, drive):
        """react to media change events."""
        self.log.error('Media change: looking for %s in %s', medium, drive)
        return False

class LogInstallProgress(apt.progress.InstallProgress):
    def __init(self, log):
        super(LogInstallProgress,self).__init__()
        self.log = log
    def error(self, pkg, errormsg):
        self.log.error("installing %s: %s", pkg, errormsg)
    def conffile(self, current, new):
        self.log.info("conffile: %s -> %s", current, new)
    def statusChange(self, pkg, percent, status):
        self.log.info("status: %s %s %s", pkg, percent, status)

class configurationError(Exception):
    pass

class parseError(configurationError):
    pass

class notfoundError(configurationError):
    pass

class usageError(configurationError):
    pass

class configOptionParser(optparse.OptionParser):
    def exit(self, status=0, msg=None):
        if status or msg:
            raise parseError(msg)

    def error(self, msg):
        raise parseError(msg)

class state(object):
    "Configuration manager for apt-assert"
    
    def __init__(self, options, log, classes):
        self.options = options
        self.log = log
        self.classes = classes

        self.commands = dict((name[4:], getattr(self, name)(self))
                             for name in dir(self) if name.startswith('cmd_'))
        self.act = True
        self.log.debug('act is %s', self.act)
        self.cache = apt.Cache()

    class confcommand(object):
        def __init__(self, state):
            self.state = state
            self.log = state.log
        def call(self, argv):
            self.run(argv)
        def run(self, argv):
            self.log.error('%s is unimplemented', self.__class__.__name__)

    class action(confcommand):
        def call(self, argv):
            if self.state.act:
                super(state.action, self).call(argv)

    class cmd_upgrade(action):
        def run(self, argv):
            parser = configOptionParser(add_help_option=False)
            parser.add_option('--component', dest='component')
            parser.add_option('--archive', dest='archive')
            parser.add_option('--origin', dest='origin')
            parser.add_option('--label', dest='label')
            parser.add_option('--site', dest='site')
            parser.add_option('--trusted', dest='trusted', action='store_true')
            (options, args) = parser.parse_args(argv)
            if args[1:]:
                raise parseError('spurious args', args[1:])
            restrictions = [(val, getattr(options, val))
                            for val in ('component', 'archive', 'origin', 'label', 'site', 'trusted')
                            if getattr(options, val)]
            self.log.debug('walking the cache for upgrade, restrictions=%s', restrictions)
            for p in self.state.cache:
                if p.isInstalled and p.installed < p.candidate and p.isUpgradable:
                    if not restrictions or any(all(getattr(o, k) == v
                                                   for (k,v) in restrictions)
                                               for o in p.candidate.origins):
                        self.log.debug('marking %s for upgrade', p)
                        p.markUpgrade()
            self.log.debug('done walking the cache for upgrade')

    class cmd_install(action):
        pass

    class cmd_remove(action):
        pass

    class cmd_hold(action):
        pass

    class cmd_classfile(confcommand):
        def run(self, argv):
            if len(argv) != 2:
                raise parseError('classfile takes exactly one argument')
            if self.state.classes is None:
                self.state.classes = set(readclasses(argv[1]))
            self.log.debug('classes from "%s": %s', argv[1], ' '.join(sorted(self.state.classes)))

    class cmd_class(confcommand):
        def run(self, argv):
            if len(argv) != 2:
                raise parseError('class takes exactly one argument')
            if self.state.classes is not None and argv[1] in self.state.classes:
                self.state.act = True
            else:
                self.state.act = False
            self.log.debug('state.act = %s', self.state.act)

    def go(self):
        if self.options.dry_run:
            self.log.warn('Not updating package lists')
        else:
            try:
                self.cache.update(LogFetchProgress(self.log))
            except Exception:
                self.log.exception('ignoring exception from update')

        for (lineno, cmd) in readconf(self.options.conffile):
            self.log.debug('command: "%s"', ' '.join(cmd))
            if cmd[0] in self.commands:
                self.commands[cmd[0]].call(cmd)
            else:
                raise notfoundError('At line %d: not such command %s' % (lineno, cmd[0]), lineno)

        self.log.debug("walking the cache to see what we'd do")
        for p in self.cache:
            flags = [v
                     for (k, v) in [('markedInstall', 'install'),
                                    ('markedDelete', 'delete'),
                                    ('markedUpgrade', 'upgrade'),
                                    ('markedDowngrade', 'downgrade'),
                                    ('markedKeep', 'keep'),
                                    ('markedReinstall', 'reinstall'),
                                    ]
                     if getattr(p, k)]
            if flags:
                self.log.info('%s -> %s', p, ' '.join(flags))

        if not self.options.dry_run:
            self.log.debug('committing...')
            self.cache.commit(LogFetchProgress(self.log), LogInstallProgress(self.log))
        else:
            self.log.warn('not committing')

def readconf(filename):
    fp = open(filename)
    for (lineno, line) in enumerate(fp):
        try:
            parsed = shlex.split(line, True)
        except Exception, e:
            raise parseError('At line %d: %s' % (lineno + 1, e), lineno + 1, e)
        if parsed:
            yield lineno + 1, parsed
    fp.close()

def readclasses(filename):
    for name in itertools.chain(*(parsed for (lineno, parsed) in readconf(filename))):
        yield name

def main(argv):
    parser = optparse.OptionParser()
    parser.add_option('-c', '--conf', dest='conffile',
                      help='configuration file', default='conf')
    parser.add_option('-n', '--dry-run', dest='dry_run', action='store_true',
                      help="don't actually do anything")
    parser.add_option('-v', '--verbose', dest='verbose', action='count', default=0,
                      help='increase verbosity')
    parser.add_option('-C', '--class-file', dest='classfile', default=None,
                      help='file with a list of classes (overrides configuration directive)')
    parser.add_option('--classes', dest='classes', default=None,
                      help='all-overriding list of classes')
    (options, args) = parser.parse_args(argv)

    loglevel = max(logging.WARNING - options.verbose*10, logging.DEBUG)
    logging.basicConfig(level = loglevel,
                        format = '%(asctime)s %(name)s.%(funcName)s:%(lineno)d %(message)s')
    log = logging.getLogger(os.path.basename(argv[0] or 'uptitude'))
    log.debug('loglevel is %d', loglevel)

    classes = None
    if options.classes:
        classes = set(re.split(r'[\W+]', options.classes))
        log.debug('classes from command line: %s', ' '.join(sorted(classes)))
    elif options.classfile:
        classes = set(readclasses(options.classfile))
        log.debug('classes from "%s": %s', options.classfile, ' '.join(sorted(classes)))

    conf = state(options, log, classes)
    conf.go()

if __name__ == '__main__':
    try:
        main(sys.argv)
    except SystemExit:
        raise
    except:
        logging.exception('at top level')
