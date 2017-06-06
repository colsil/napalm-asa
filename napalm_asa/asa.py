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

"""
Napalm driver for Cisco ASA.

Read https://napalm.readthedocs.io for more information.
"""
from __future__ import print_function
from __future__ import unicode_literals
from difflib import unified_diff
import re
from napalm_base.base import NetworkDriver
from napalm_base.utils import py23_compat
from napalm_ios import IOSDriver

from netmiko import ConnectHandler


class AsaDriver(NetworkDriver):
    """Napalm driver for Cisco ASA."""

    def __init__(self, hostname, username, password, timeout=60, optional_args=None):
        """Constructor."""
        self.device = None
        self.hostname = hostname
        self.username = username
        self.password = password
        self.timeout = timeout

        self.candidate_config = None

        self.dest_file_system = None

        if optional_args is None:
            optional_args = {}
        else:
            self.context = optional_args.get('context', None)

    def open(self):
        """Implementation of NAPALM method open."""
        self.device = ConnectHandler(device_type='cisco_asa',
                                     host=self.hostname,
                                     username=self.username,
                                     password=self.password)
        # ensure in enable mode
        self.device.enable()
        # change to system context
        self.device.send_command("changeto system")
        if not self.dest_file_system:
            try:
                self.dest_file_system = self.device._autodetect_fs()
            except AttributeError:
                raise AttributeError("Netmiko _autodetect_fs not found please upgrade Netmiko or "
                                     "specify dest_file_system in optional_args.")
        if self.context and self.context != 'system':
            self.device.send_command("changeto context " + self.context)

    def close(self):
        """Implementation of NAPALM method close."""
        self.device.disconnect()

    @staticmethod
    def _send_command_postprocess(output):
        """
        Keep same structure as for ios module but don't do anything for now
        """
        return output

    def _send_command(self, command):
        """Wrapper for self.device.send.command().
        If command is a list will iterate through commands until valid command.
        """
        output = ""
        if isinstance(command, list):
            for cmd in command:
                output = self.device.send_command(cmd)
                if "% Invalid" not in output:
                    break
        else:
            output = self.device.send_command(command)
        return self._send_command_postprocess(output)

    def get_config(self, retrieve='all'):
        """Implementation of get_config for Cisco ASA.
        Returns the startup or/and running configuration as dictionary.
        The keys of the dictionary represent the type of configuration
        (startup or running). The candidate is always empty string,
        since Cisco ASA does not support candidate configuration.
        """

        configs = {
            'startup': '',
            'running': '',
            'candidate': '',
        }

        if retrieve in ('startup', 'all'):
            command = 'show startup-config'
            output = self._send_command(command)
            configs['startup'] = output

        if retrieve in ('running', 'all'):
            command = 'show running-config'
            output = self._send_command(command)
            configs['running'] = output

        return configs

    def load_replace_candidate(self, filename=None, config=None):
        if filename:
            with open(filename, 'r') as file:
                self.candidate_config = file.read()
        elif config:
            self.candidate_config = config
        return True, "Candidate loaded to memory (no ASA support)"

    def compare_config(self):
        running_config = self.get_config(retrieve='running')['running']
        running_config = running_config.splitlines()
        candidate_config = self.candidate_config.splitlines()
        diff = unified_diff(running_config, candidate_config)
        return "\n".join(diff)

    def discard_config(self):
        self.candidate_config = None

    def commit_config(self):
        raise NotImplementedError

    def get_lldp_neighbors(self):
        '''ASA implementation of get_lldp_neighbors
        Always returns empty dict as ASA does not support CDP or LLDP
        '''
        return {}

    def get_lldp_neighbors_detail(self, interface=""):
        """"ASA Implementation of get_lldp_neighbors_detail
        Always returns empty dict as ASA does not support CDP or LLDP
        """
        return {}

    def get_facts(self):
        vendor = u'Cisco'
        uptime = -1
        serial_number, fqdn, os_version, hostname, model = (u'Unknown', u'Unknown', u'Unknown', u'Unknown', u'Unknown')

        show_ver = self._send_command('show version')
        show_hostname = self._send_command('show hostname')
        show_fqdn = self._send_command('show hostname fqdn')
        show_inventory = self._send_command('show inventory')
        show_interfaces = self._send_command('show interface ip brief')

        # Hostname and FQDN are returned by show commands without any other output
        hostname = show_hostname.strip()
        fqdn = show_fqdn.strip()

        # Parse show version command
        # Gather os version, uptime and serial number
        for line in show_ver.splitlines():
            if 'Cisco Adaptive Security Appliance Software Version' in line:
                os_version_match = re.match(r"Cisco Adaptive Security Appliance Software Version (\S*)", line)
                os_version = os_version_match.group(1)
            if hostname + ' up ' in line:
                _, uptime_str = line.split(' up ')
                uptime = IOSDriver.parse_uptime(uptime_str)
            if "Serial Number: " in line:
                _, serial_number = line.split(' Number: ')
                serial_number = serial_number.strip()

        chassis_flag = False
        for line in show_inventory.splitlines():
            if "Name: \"Chassis\"" in line:
                chassis_flag = True
            if chassis_flag and "PID: " in line:
                match = re.search(r'PID: (\S*) .*',line)
                model = match.group(1)
                chassis_flag = False

        # Build interface list
        interface_list = []
        for line in show_interfaces.splitlines():
            interface_match = re.search(r'\S+\d+\/\d+\.?\d*',line)
            if interface_match:
                interface_list.append(interface_match.group(0))

        return {
            'uptime': uptime,
            'vendor': vendor,
            'os_version': py23_compat.text_type(os_version),
            'serial_number': py23_compat.text_type(serial_number),
            'model': py23_compat.text_type(model),
            'hostname': py23_compat.text_type(hostname),
            'fqdn': fqdn,
            'interface_list': interface_list
        }
