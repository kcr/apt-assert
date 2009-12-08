#!/usr/bin/python

from apt.cache import Cache, Filter, FilteredCache
from apt.progress import TextFetchProgress

cache = Cache()

cache.update(TextFetchProgress())

class InstalledFilter(Filter):
    """ Filter that returns the currently installed packages """

    def apply(self, pkg):
        return bool(pkg.installed)

class UpgradableFilter(InstalledFilter):
    """ Filter that returns installed, upgradable packagess """

    def apply(self, pkg):
        return super(UpgradableFilter, self).apply(pkg) and  pkg.installed < pkg.candidate
    

filtered = FilteredCache(cache)
filtered.setFilter(UpgradableFilter())

for p in filtered:
    if p.installed < p.candidate and any(o.label=='Debian-Security' and o.trusted for o in p.candidate.origins):
        print p.candidate
