#!/usr/bin/python

import unittest

import uptitude

class propdict(dict):
    "strongly inspired by web.py's Storage"
    def __getattr__(self, k):
        return self[k]
    def __setattr__(self, k, v):
        self[k] = v
    def __delattr__(self, k):
        del self[k]
    def __repr__(self):
        return self.__class__.__module__ + '.' + self.__class__.__name__ + '(' + dict.__repr__(self) + ')'

class uptitudeTest(unittest.TestCase):
    def testFilters(self):
        filt = uptitude.InstalledFilter()
        self.failUnless(filt.apply(propdict(installed = True)))
        self.failUnless(not filt.apply(propdict(installed = False)))

        filt = uptitude.UpgradableFilter()
        self.failUnless(filt.apply(propdict(installed = 1, candidate = 2)))
        self.failUnless(not filt.apply(propdict(installed = 1, candidate = 0)))
        self.failUnless(not filt.apply(propdict(installed = 0, candidate = 1)))
        self.failUnless(not filt.apply(propdict(installed = 0, candidate = -1)))

if __name__ == '__main__':
    unittest.main()
