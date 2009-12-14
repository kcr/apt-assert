#!/usr/bin/python

from __future__ import with_statement

import unittest

import logging

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

class propdictTest(unittest.TestCase):
    def test(self):
        d = propdict({'a': 1})
        self.failUnlessEqual(repr(d), "__main__.propdict({'a': 1})")
        self.failUnlessEqual(d['a'], 1)
        self.failUnlessEqual(d.a, 1)
        d.a = 2
        self.failUnlessEqual(d['a'], 2)
        self.failUnlessEqual(d.a, 2)
        self.failUnlessRaises(KeyError, lambda: d.b)
        del d.a
        self.failUnlessRaises(KeyError, lambda: d.a)

class mocked(object):
    def __init__(self, target, **kw):
        self.target = target
        self.stash = {}
        self.map = kw
    def __enter__(self):
        for k in self.map:
            self.stash[k] = getattr(self.target, k)
            setattr(self.target, k, self.map[k])
        return self
    def __exit__(self, type, value, traceback):
        for k in self.map:
            setattr(self.target, k, self.stash[k])
        return False

class mockedTest(unittest.TestCase):
    def test(self):
        d = propdict(a=1, b=2, c=3)
        m = mocked(d, a=11, b=22, c=33)

        self.assertEqual(d['a'], 1)
        self.assertEqual(d['b'], 2)
        self.assertEqual(d['c'], 3)
        self.assertEqual(tuple(sorted(d.keys())),
                         ('a', 'b', 'c'))

        self.assertEqual(m.__enter__(), m)
        self.assertEqual(d['a'], 11)
        self.assertEqual(d['b'], 22)
        self.assertEqual(d['c'], 33)
        self.assertEqual(tuple(sorted(d.keys())),
                         ('a', 'b', 'c'))

        self.assertEqual(m.__exit__(None, None, None), False)
        self.assertEqual(d['a'], 1)
        self.assertEqual(d['b'], 2)
        self.assertEqual(d['c'], 3)
        self.assertEqual(tuple(sorted(d.keys())),
                         ('a', 'b', 'c'))

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
    def testState(self):
        cd = propdict()
        with mocked(uptitude, apt = propdict(Cache = object)):
            state = uptitude.state(propdict(dry_run = True),
                                            logging.getLogger('uptitude_test'))
            self.failUnless(state.commands)
            self.failUnless(not state.act)
            self.failUnless(state.log)
            self.failUnless(state.options)
            self.failUnless(state.cache)


if __name__ == '__main__':
    unittest.main()
