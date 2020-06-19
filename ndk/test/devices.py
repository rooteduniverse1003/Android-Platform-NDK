#
# Copyright (C) 2017 The Android Open Source Project
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
"""Device wrappers and device fleet management."""
from __future__ import print_function

import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Set

from ndk.abis import Abi
import ndk.ext.shutil
import ndk.paths
from ndk.test.spec import BuildConfiguration
from ndk.workqueue import ShardingGroup, Worker, WorkQueue

try:
    import adb  # pylint: disable=import-error
except ImportError:
    import site
    site.addsitedir(ndk.paths.android_path('development/python-packages'))
    import adb  # pylint: disable=import-error,ungrouped-imports


def logger() -> logging.Logger:
    """Returns the module logger."""
    return logging.getLogger(__name__)


class Device(adb.AndroidDevice):
    """A device to be used for testing."""
    # pylint: disable=no-member
    def __init__(self, serial: str, precache: bool = False) -> None:
        super().__init__(serial)
        self._did_cache = False
        self._cached_abis: Optional[List[Abi]] = None
        self._ro_build_characteristics: Optional[str] = None
        self._ro_build_id: Optional[str] = None
        self._ro_build_version_sdk: Optional[str] = None
        self._ro_build_version_codename: Optional[str] = None
        self._ro_debuggable: Optional[bool] = None
        self._ro_product_name: Optional[str] = None

        if precache:
            self.cache_properties()

    def cache_properties(self) -> None:
        """Caches the device's system properties."""
        if not self._did_cache:
            self._ro_build_characteristics = self.get_prop(
                'ro.build.characteristics')
            self._ro_build_id = self.get_prop('ro.build.id')
            self._ro_build_version_sdk = self.get_prop('ro.build.version.sdk')
            self._ro_build_version_codename = self.get_prop(
                'ro.build.version.codename')
            self._ro_debuggable = self.get_prop('ro.debuggable')
            self._ro_product_name = self.get_prop('ro.product.name')
            self._did_cache = True

            # 64-bit devices list their ABIs differently than 32-bit devices.
            # Check all the possible places for stashing ABI info and merge
            # them.
            abi_properties = [
                'ro.product.cpu.abi',
                'ro.product.cpu.abi2',
                'ro.product.cpu.abilist',
            ]
            abis: Set[Abi] = set()
            for abi_prop in abi_properties:
                value = self.get_prop(abi_prop)
                if value is not None:
                    abis.update(value.split(','))

            self._cached_abis = sorted(list(abis))

    @property
    def name(self) -> str:
        self.cache_properties()
        assert self._ro_product_name is not None
        return self._ro_product_name

    @property
    def version(self) -> int:
        self.cache_properties()
        assert self._ro_build_version_sdk is not None
        return int(self._ro_build_version_sdk)

    @property
    def abis(self) -> List[Abi]:
        """Returns a list of ABIs supported by the device."""
        self.cache_properties()
        assert self._cached_abis is not None
        return self._cached_abis

    @property
    def build_id(self) -> str:
        self.cache_properties()
        assert self._ro_build_id is not None
        return self._ro_build_id

    @property
    def is_release(self) -> bool:
        self.cache_properties()
        codename = self._ro_build_version_codename
        return codename == 'REL'

    @property
    def is_emulator(self) -> bool:
        self.cache_properties()
        chars = self._ro_build_characteristics
        return chars == 'emulator'

    @property
    def is_debuggable(self) -> bool:
        self.cache_properties()
        assert self._ro_debuggable is not None
        return int(self._ro_debuggable) != 0

    def can_run_build_config(self, config: BuildConfiguration) -> bool:
        assert config.api is not None
        if self.version < config.api:
            # Device is too old for this test.
            return False

        if config.abi not in self.abis:
            return False

        return True

    @property
    def supports_pie(self) -> bool:
        return self.version >= 16

    def __str__(self) -> str:
        return (
            f'android-{self.version} {self.name} {self.serial} {self.build_id}'
        )

    def __eq__(self, other: object) -> bool:
        assert isinstance(other, Device)
        return self.serial == other.serial

    def __hash__(self) -> int:
        return hash(self.serial)


class DeviceShardingGroup(ShardingGroup):
    """A collection of devices that should be identical for testing purposes.

    For the moment, devices are only identical for testing purposes if they are
    the same hardware running the same build.
    """
    def __init__(self, first_device: Device) -> None:
        self.devices = [first_device]
        self.abis = sorted(first_device.abis)
        self.version = first_device.version
        self.is_emulator = first_device.is_emulator
        self.is_release = first_device.is_release
        self.is_debuggable = first_device.is_debuggable

    def __str__(self) -> str:
        return f'android-{self.version} {" ".join(self.abis)}'

    @property
    def shards(self) -> List[Any]:
        return self.devices

    def add_device(self, device: Device) -> None:
        if not self.device_matches(device):
            raise ValueError(f'{device} does not match this device group.')

        self.devices.append(device)

    def device_matches(self, device: Device) -> bool:
        if self.version != device.version:
            return False
        if self.abis != device.abis:
            return False
        if self.is_emulator != device.is_emulator:
            return False
        if self.is_release != device.is_release:
            return False
        if self.is_debuggable != device.is_debuggable:
            return False
        return True

    def __eq__(self, other: object) -> bool:
        assert isinstance(other, DeviceShardingGroup)
        if self.version != other.version:
            return False
        if self.abis != other.abis:
            return False
        if self.is_emulator != other.is_emulator:
            return False
        if self.is_release != other.is_release:
            return False
        if self.is_debuggable != other.is_debuggable:
            return False
        if self.devices != other.devices:
            print('devices not equal: {}, {}'.format(
                self.devices, other.devices))
            return False
        return True

    def __lt__(self, other: object) -> bool:
        assert isinstance(other, DeviceShardingGroup)
        return (self.version, self.abis) < (other.version, other.abis)

    def __hash__(self) -> int:
        return hash((
            self.version, self.is_emulator, self.is_release,
            self.is_debuggable, tuple(self.abis), tuple(self.devices)))


class DeviceFleet:
    """A collection of devices that can be used for testing."""
    def __init__(self, test_configurations: Dict[int, List[Abi]]) -> None:
        """Initializes a device fleet.

        Args:
            test_configurations: Dict mapping API levels to a list of ABIs to
                test for that API level. Example:

                    {
                        15: ['armeabi', 'armeabi-v7a'],
                        16: ['armeabi', 'armeabi-v7a', 'x86'],
                    }
        """
        self.devices: Dict[int, Dict[Abi, Optional[DeviceShardingGroup]]] = {}
        for api, abis in test_configurations.items():
            self.devices[int(api)] = {abi: None for abi in abis}

    def add_device(self, device: Device) -> None:
        """Fills a fleet device slot with a device, if appropriate."""
        if device.version not in self.devices:
            logger().info('Ignoring device for unwanted API level: %s', device)
            return

        same_version = self.devices[device.version]
        for abi, current_group in same_version.items():
            # This device can't fulfill this ABI.
            if abi not in device.abis:
                continue

            # Never houdini.
            if abi.startswith('armeabi') and 'x86' in device.abis:
                continue

            # Anything is better than nothing.
            if current_group is None:
                self.devices[device.version][abi] = DeviceShardingGroup(device)
                continue

            if current_group.device_matches(device):
                current_group.add_device(device)
                continue

            # The emulator images have actually been changed over time, so the
            # devices are more trustworthy.
            if current_group.is_emulator and not device.is_emulator:
                self.devices[device.version][abi] = DeviceShardingGroup(device)

            # Trust release builds over pre-release builds, but don't block
            # pre-release because sometimes that's all there is.
            if not current_group.is_release and device.is_release:
                self.devices[device.version][abi] = DeviceShardingGroup(device)

    def get_unique_device_groups(self) -> Set[DeviceShardingGroup]:
        groups = set()
        for version in self.get_versions():
            for abi in self.get_abis(version):
                group = self.get_device_group(version, abi)
                if group is not None:
                    groups.add(group)
        return groups

    def get_device_group(self, version: int,
                         abi: Abi) -> Optional[DeviceShardingGroup]:
        """Returns the device group associated with the given API and ABI."""
        if version not in self.devices:
            return None
        if abi not in self.devices[version]:
            return None
        return self.devices[version][abi]

    def get_missing(self) -> List[str]:
        """Describes desired configurations without available deices."""
        missing = []
        for version, abis in self.devices.items():
            for abi, group in abis.items():
                if group is None:
                    missing.append(f'android-{version} {abi}')
        return missing

    def get_versions(self) -> List[int]:
        """Returns a list of all API levels in this fleet."""
        return list(self.devices.keys())

    def get_abis(self, version: int) -> List[Abi]:
        """Returns a list of all ABIs for the given API level in this fleet."""
        return list(self.devices[version].keys())


def create_device(_worker: Worker, serial: str, precache: bool) -> Device:
    return Device(serial, precache)


def get_all_attached_devices(workqueue: WorkQueue) -> List[Device]:
    """Returns a list of all connected devices."""
    if shutil.which('adb') is None:
        raise RuntimeError('Could not find adb.')

    # We could get the device name from `adb devices -l`, but we need to
    # getprop to find other details anyway, and older devices don't report
    # their names properly (nakasi on android-16, for example).
    p = subprocess.run(['adb', 'devices'],
                       check=True,
                       stdout=subprocess.PIPE,
                       encoding='utf-8')
    if p.returncode != 0:
        raise RuntimeError('Failed to get list of devices from adb.')

    # The first line of `adb devices` just says "List of attached devices", so
    # skip that.
    for line in p.stdout.split('\n')[1:]:
        if not line.strip():
            continue

        serial, _ = re.split(r'\s+', line, maxsplit=1)

        if 'offline' in line:
            logger().info('Ignoring offline device: %s', serial)
            continue
        if 'unauthorized' in line:
            logger().info('Ignoring unauthorized device: %s', serial)
            continue

        # Caching all the device details via getprop can actually take quite a
        # bit of time. Do it in parallel to minimize the cost.
        workqueue.add_task(create_device, serial, True)

    devices = []
    while not workqueue.finished():
        device = workqueue.get_result()
        logger().info('Found device %s', device)
        devices.append(device)

    return devices


def exclude_device(device: Device) -> bool:
    """Returns True if a device should be excluded from the fleet."""
    exclusion_list_env = os.getenv('NDK_DEVICE_EXCLUSION_LIST')
    if exclusion_list_env is None:
        return False
    exclusion_list = Path(exclusion_list_env).read_text().splitlines()
    return device.serial in exclusion_list


def find_devices(sought_devices: Dict[int, List[Abi]],
                 workqueue: WorkQueue) -> DeviceFleet:
    """Detects connected devices and returns a set for testing.

    We get a list of devices by scanning the output of `adb devices` and
    matching that with the list of desired test configurations specified by
    `sought_devices`.
    """
    fleet = DeviceFleet(sought_devices)
    for device in get_all_attached_devices(workqueue):
        if not exclude_device(device):
            fleet.add_device(device)

    return fleet
