#!/usr/bin/python

import sys, shlex
import apt

class InstalledFilter(apt.cache.Filter):
    """ Filter that returns the currently installed packages """

    def apply(self, pkg):
        return bool(pkg.installed)

class UpgradableFilter(InstalledFilter):
    """ Filter that returns installed, upgradable packagess """

    def apply(self, pkg):
        return super(UpgradableFilter, self).apply(pkg) and  pkg.installed < pkg.candidate

class configuration(object):
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
            print self.__class__.__name__, 'is unimplemented'
    class action(confcommand):
        def call(self, argv):
            if self.conf.act:
                super(configuration.action, self).call(argv)
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
    def readconf(filename):
        fp = open(filename)
        for (lineno, line) in enumerate(fp):
            try:
                parsed = shlex.split(line, True)
            except Exception, e:
                raise configuration.parseerror('At line %d: %s' % (lineno + 1, e), lineno + 1, e)
            if parsed:
                yield lineno + 1, parsed
        fp.close()
    def __init__(self, filename):
        self.commands = dict((name[4:], getattr(self, name)(self))
                             for name in dir(self) if name.startswith('cmd_'))
        self.act = True
        for (lineno, cmd) in self.readconf(filename):
            if cmd[0] in self.commands:
                self.commands[cmd[0]].call(cmd)
            else:
                raise notfoundError('At line %d: not such command %s' % (lineno, cmd[0]), lineno)

def main(argv):
    cache = apt.Cache()

    conf = configuration('conf')

    try:
        cache.update(apt.progress.TextFetchProgress())
    except Exception, e:
        print e
        print 'continuing...'

    filtered = apt.cache.FilteredCache(cache)
    filtered.setFilter(UpgradableFilter())

    for p in filtered:
        if p.installed < p.candidate and any(o.label=='Debian-Security' and o.trusted for o in p.candidate.origins):
            print p.candidate

if __name__ == '__main__':
    main(sys.argv)
