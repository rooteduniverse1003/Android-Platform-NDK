#!/usr/bin/env python
#
# Copyright (C) 2018 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Test for ndk.deps."""
import unittest

from ndk.deps import CyclicDependencyError
from ndk.deps import DependencyManager


# A basic cycle. The cycle logic is tested more thoroughly in test_graph.py,
# but we want to ensure that CyclicDependencyError is formatted nicely.
class CycleA(object):
    name = 'cycleA'
    deps = {'cycleB'}


class CycleB(object):
    name = 'cycleB'
    deps = {'cycleA'}


# A module with no dependents or dependencies. Should be immediately buildable.
class Isolated(object):
    name = 'isolated'
    deps = set()


# A module that is not present in the build graph.
class Unknown(object):
    name = 'unknown'
    deps = set()


# A simple chain of two modules. The first should be immediately buildable, and
# the second should become buildable after it completes.
class SimpleA(object):
    name = 'simpleA'
    deps = set()


class SimpleB(object):
    name = 'simpleB'
    deps = {'simpleA'}


# Slightly more complex module graph.
class ComplexA(object):
    name = 'complexA'
    deps = set()


class ComplexB(object):
    name = 'complexB'
    deps = {'complexA'}


class ComplexC(object):
    name = 'complexC'
    deps = {'complexA'}


class ComplexD(object):
    name = 'complexD'
    deps = {'complexA', 'complexB'}


class DependencyManagerTest(unittest.TestCase):
    def test_cyclic_dependency_message(self):
        """Test that a cycle raises the proper exception."""
        pattern = '^Detected cyclic dependency: cycleA -> cycleB -> cycleA$'
        with self.assertRaisesRegexp(CyclicDependencyError, pattern):
            DependencyManager([CycleA(), CycleB()])

    def test_empty_raises(self):
        """Test that an empty module list raises."""
        with self.assertRaises(ValueError):
            DependencyManager([])

    def test_complete_invalid_module_raises(self):
        """Test that completing an unknown module raises."""
        isolated = Isolated()
        unknown = Unknown()
        deps = DependencyManager([isolated])
        with self.assertRaises(KeyError):
            deps.complete(unknown)

    def test_isolated(self):
        """Test module graph with a single isolated vertex."""
        isolated = Isolated()
        deps = DependencyManager([isolated])
        self.assertSetEqual({isolated}, deps.buildable_modules)
        self.assertSetEqual({isolated}, deps.get_buildable())
        self.assertSetEqual(set(), deps.buildable_modules)
        deps.complete(isolated)

    def test_simple(self):
        """Test module graph with a simple module chain."""
        simpleA = SimpleA()
        simpleB = SimpleB()
        deps = DependencyManager([simpleA, simpleB])
        self.assertSetEqual({simpleB}, set(deps.blocked_modules.keys()))
        self.assertSetEqual({simpleA}, deps.buildable_modules)
        self.assertSetEqual({simpleA}, deps.get_buildable())
        self.assertSetEqual(set(), deps.buildable_modules)
        deps.complete(simpleA)
        self.assertSetEqual(set(), set(deps.blocked_modules.keys()))
        self.assertSetEqual({simpleB}, deps.buildable_modules)
        self.assertSetEqual({simpleB}, deps.get_buildable())
        self.assertSetEqual(set(), deps.buildable_modules)
        deps.complete(simpleB)

    def test_complex(self):
        """Test module graph with a more complex module chain."""
        complexA = ComplexA()
        complexB = ComplexB()
        complexC = ComplexC()
        complexD = ComplexD()
        deps = DependencyManager([complexA, complexB, complexC, complexD])
        self.assertSetEqual(
            {complexB, complexC, complexD}, set(deps.blocked_modules.keys()))
        self.assertSetEqual({complexA}, deps.buildable_modules)
        self.assertSetEqual({complexA}, deps.get_buildable())
        self.assertSetEqual(set(), deps.buildable_modules)
        deps.complete(complexA)
        self.assertSetEqual({complexD}, set(deps.blocked_modules.keys()))
        self.assertSetEqual({complexB, complexC}, deps.buildable_modules)
        self.assertSetEqual({complexB, complexC}, deps.get_buildable())
        self.assertSetEqual(set(), deps.buildable_modules)
        deps.complete(complexC)
        self.assertSetEqual({complexD}, set(deps.blocked_modules.keys()))
        self.assertSetEqual(set(), deps.buildable_modules)
        self.assertSetEqual(set(), deps.get_buildable())
        deps.complete(complexB)
        self.assertSetEqual(set(), set(deps.blocked_modules.keys()))
        self.assertSetEqual({complexD}, deps.buildable_modules)
        self.assertSetEqual({complexD}, deps.get_buildable())
        self.assertSetEqual(set(), deps.buildable_modules)
        deps.complete(complexD)
