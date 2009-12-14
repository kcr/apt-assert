#!/usr/bin/python

import sys, os, shlex, logging, optparse
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

class state(object):
    "Configuration manager for apt-assert"
    
    class configurationError(Exception):
        pass

    class parseError(configurationError):
        pass

    class notfoundError(configurationError):
        pass

    class confcommand(object):
        def __init__(self, conf):
            self.conf = conf
        def call(self, argv):
            self.run(argv)
        def run(self, argv):
            self.conf.log.error('%s is unimplemented', self.__class__.__name__)

    class action(confcommand):
        def call(self, argv):
            if self.conf.act:
                super(state.action, self).call(argv)

    class cmd_upgrade(action):
        pass

    class cmd_install(action):
        pass

    class cmd_remove(action):
        pass

    class cmd_hold(action):
        pass

    class cmd_class(confcommand):
        pass

    @staticmethod
    def __readconf(filename):
        fp = open(filename)
        for (lineno, line) in enumerate(fp):
            try:
                parsed = shlex.split(line, True)
            except Exception, e:
                raise state.parseerror('At line %d: %s' % (lineno + 1, e), lineno + 1, e)
            if parsed:
                yield lineno + 1, parsed
        fp.close()

    def __init__(self, filename, log = None):
        self.commands = dict((name[4:], getattr(self, name)(self))
                             for name in dir(self) if name.startswith('cmd_'))
        self.act = True
        self.log = log if log is not None else logging.getLogger('uptitude.state')
        for (lineno, cmd) in self.__readconf(filename):
            if cmd[0] in self.commands:
                self.commands[cmd[0]].call(cmd)
            else:
                raise notfoundError('At line %d: not such command %s' % (lineno, cmd[0]), lineno)

def main(argv):
    parser = optparse.OptionParser()
    parser.add_option('-c', '--conf', dest='conffile',
                      help='configuration file', default='conf')
    parser.add_option('-v', '--verbose', dest='verbose', action='count',
                      help='increase verbosity')
    (options, args) = parser.parse_args(argv)

    level = logging.DEBUG #logging.WARNING
    level -= max(options.verbose*10, level - logging.DEBUG)
    logging.basicConfig(level = logging.DEBUG,
                        format = '%(asctime)s %(name)s.%(funcName)s:%(lineno)d %(message)s')
    log = logging.getLogger(os.path.basename(argv[0] or 'uptitude'))

    cache = apt.Cache()

    conf = state(options.conffile, log = log)

    try:
        cache.update(LogFetchProgress(log))
    except Exception:
        log.exception('ignoring exception from update')

    filtered = apt.cache.FilteredCache(cache)
    filtered.setFilter(UpgradableFilter())

    for p in filtered:
        if p.installed < p.candidate and any(o.label=='Debian-Security' and o.trusted for o in p.candidate.origins):
            log.info('%s is upgradable (from %s)', p.candidate, p.candidate.origins)

if __name__ == '__main__':
    try:
        main(sys.argv)
    except SystemExit:
        raise
    except:
        logging.exception('at top level')
