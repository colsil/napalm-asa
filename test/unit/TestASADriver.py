# Copyright 2015 Spotify AB. All rights reserved.
#
# The contents of this file are licensed under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with the
# License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

"""Tests for ASADriver."""

import unittest

from napalm_asa import asa

from napalm_base.test.base import TestConfigNetworkDriver


class TestConfigASADriver(unittest.TestCase, TestConfigNetworkDriver):

    @classmethod
    def setUpClass(cls):
        """Executed when the class is instantiated."""
        ip_addr = '172.16.179.129'
        username = 'vagrant'
        password = 'vagrant'
        cls.vendor = 'asa'

        cls.device = asa.AsaDriver(ip_addr, username, password)
        cls.device.open()

        cls.device.load_replace_candidate(filename='%s/initial.conf' % cls.vendor)
        cls.device.commit_config()

    def test_load_template(self):
        raise unittest.SkipTest()

    def test_merge_configuration(self):
        raise unittest.SkipTest()

    def test_merge_configuration_typo_and_rollback(self):
        raise unittest.SkipTest()

    def test_replacing_config_and_rollback(self):
        raise unittest.SkipTest()

    def test_replacing_config_with_typo(self):
        raise unittest.SkipTest()


# class TestGetterASADriver(unittest.TestCase, TestGettersNetworkDriver):
#     """Getters Tests for ASADriver.
#     Get operations:
#     get_lldp_neighbors
#     get_facts
#     get_interfaces
#     get_bgp_neighbors
#     get_interfaces_counters
#     """
#
#     @classmethod
#     def setUpClass(cls):
#         """Executed when the class is instantiated."""
#         cls.mock = False
#
#         username = 'vagrant'
#         ip_addr = '172.16.179.129'
#         password = 'vagrant'
#         cls.vendor = 'asa'
#         optional_args = {}
#         optional_args['dest_file_system'] = 'disk0:'
#
#         cls.device = asa.AsaDriver(ip_addr, username, password, optional_args=optional_args)
#
#         if cls.mock:
#             cls.device.device = FakeASADevice()
#         else:
#             cls.device.open()


# class FakeASADevice:
#     """Class to fake a ASA Device."""
#
#     @staticmethod
#     def read_txt_file(filename):
#         """Read a txt file and return its content."""
#         with open(filename) as data_file:
#             return data_file.read()
#
#     def send_command_expect(self, command, **kwargs):
#         """Fake execute a command in the device by just returning the content of a file."""
#         cmd = re.sub(r'[\[\]\*\^\+\s\|]', '_', command)
#         output = self.read_txt_file('ios/mock_data/{}.txt'.format(cmd))
#         return py23_compat.text_type(output)
#
#     def send_command(self, command, **kwargs):
#         """Fake execute a command in the device by just returning the content of a file."""
#         return self.send_command_expect(command)
#
#     def is_alive(self):
#         return {
#             'is_alive': True  # In testing everything works..
#         }


if __name__ == "__main__":
    unittest.main()
