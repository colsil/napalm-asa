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

import re
import socket
from difflib import unified_diff

import napalm_base.constants as C
from napalm_base.base import NetworkDriver
from napalm_base.helpers import mac
from napalm_base.utils import py23_compat

from netmiko import ConnectHandler

HOUR_SECONDS = 3600
DAY_SECONDS = 24 * HOUR_SECONDS
WEEK_SECONDS = 7 * DAY_SECONDS
YEAR_SECONDS = 365 * DAY_SECONDS

MAC_REGEX = r"[a-fA-F0-9]{4}\.[a-fA-F0-9]{4}\.[a-fA-F0-9]{4}"


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

    def is_alive(self):
        """Returns a flag with the state of the SSH connection."""
        null = chr(0)
        try:
            # Try sending ASCII null byte to maintain
            #   the connection alive
            self.device.send_command(null)
        except (socket.error, EOFError):
            # If unable to send, we can tell for sure
            #   that the connection is unusable,
            #   hence return False.
            return {
                'is_alive': False
            }
        return {
            'is_alive': self.device.remote_conn.transport.is_active()
        }

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
            output = self._process_config_output(output)
            configs['startup'] = output

        if retrieve in ('running', 'all'):
            command = 'show running-config'
            output = self._send_command(command)
            output = self._process_config_output(output)
            configs['running'] = output

        return configs

    def _process_config_output(self, output):
        newoutput = ''
        for line in output.splitlines():
            # Remove non configuration output
            if re.search(r'^:', line):
                continue
            elif re.search(r'^ASA Version', line):
                continue
            elif re.search(r'^Cryptochecksum', line):
                continue
            else:
                newoutput += line + "\n"
        return newoutput

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
        """ASA does not support CDP or LLDP
        """
        raise NotImplementedError

    def get_lldp_neighbors_detail(self, interface=""):
        """"ASA does not support CDP or LLDP
        """
        raise NotImplementedError

    def get_facts(self):
        vendor = u'Cisco'
        uptime = -1
        serial_number, fqdn, os_version, hostname, model = (
            u'Unknown', u'Unknown', u'Unknown', u'Unknown', u'Unknown')

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
                os_version_match = re.match(
                    r"Cisco Adaptive Security Appliance Software Version (\S*)",
                    line
                )
                os_version = os_version_match.group(1)
            if hostname + ' up ' in line:
                _, uptime_str = line.split(' up ')
                uptime = self.parse_uptime(uptime_str)
            if "Serial Number: " in line:
                _, serial_number = line.split(' Number: ')
                serial_number = serial_number.strip()

        chassis_flag = False
        for line in show_inventory.splitlines():
            if "Name: \"Chassis\"" in line:
                chassis_flag = True
            if chassis_flag and "PID: " in line:
                match = re.search(r'PID: (\S*) .*', line)
                model = match.group(1)
                chassis_flag = False

        # Build interface list
        interface_list = []
        for line in show_interfaces.splitlines():
            interface_match = re.search(r'\S+\d+\/\d+\.?\d*', line)
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

    @staticmethod
    def parse_uptime(uptime_str):
        """
        Extract the uptime string from the given Cisco Device.

        Return the uptime in seconds as an integer
        """
        # Initialize to zero
        (years, weeks, days, hours, minutes, seconds) = (0, 0, 0, 0, 0, 0)

        uptime_str = uptime_str.strip()
        time_list = re.split(r"(\d+ \S+)", uptime_str)
        for element in time_list:
            if re.search("year", element):
                years = int(element.split()[0])
            elif re.search("week", element):
                weeks = int(element.split()[0])
            elif re.search("day", element):
                days = int(element.split()[0])
            elif re.search("hour", element):
                hours = int(element.split()[0])
            elif re.search("min", element):
                minutes = int(element.split()[0])
            elif re.search("sec", element):
                seconds = int(element.split()[0])

        uptime_sec = (years * YEAR_SECONDS) + (weeks * WEEK_SECONDS) + (days * DAY_SECONDS) + \
                     (hours * 3600) + (minutes * 60) + (seconds)
        return uptime_sec

    def ping(self, destination, source=C.PING_SOURCE, ttl=C.PING_TTL, timeout=C.PING_TIMEOUT,
             size=C.PING_SIZE, count=C.PING_COUNT, vrf=C.PING_VRF):
        """
        Execute ping on the device and returns a dictionary with the result.
        Output dictionary has one of following keys:
            * success
            * error
        In case of success, inner dictionary will have the following keys:
            * probes_sent (int)
            * packet_loss (int)
            * rtt_min (float)
            * rtt_max (float)
            * rtt_avg (float)
            * rtt_stddev (float)
            * results (list)
        'results' is a list of dictionaries with the following keys:
            * ip_address (str)
            * rtt (float)
        """
        ping_dict = {}
        # vrf in the asa world is a context
        # no support for pinging from a different context from system context
        # so change context before executing ping
        if vrf:
            output = self._send_command('changeto context {}'.format(vrf))
            if '%' in output:
                ping_dict['error'] = output

        # source must be the string nameif of the interface
        # ASA doesn't accept a source ip
        if source:
            command = 'ping {} {}'.format(source, destination)
        else:
            command = 'ping {}'.format(destination)
        command += ' timeout {}'.format(timeout)
        command += ' size {}'.format(size)
        command += ' repeat {}'.format(count)

        output = self._send_command(command)
        if '%' in output:
            ping_dict['error'] = output
        elif 'Sending' in output:
            ping_dict['success'] = {
                'probes_sent': 0,
                'probes_sent': 0,
                'packet_loss': 0,
                'rtt_min': 0.0,
                'rtt_max': 0.0,
                'rtt_avg': 0.0,
                'rtt_stddev': 0.0,
                'results': []
            }

            for line in output.splitlines():
                fields = line.split()
                if 'Success rate is 0' in line:
                    sent_and_received = re.search(r'\((\d*)/(\d*)\)', fields[5])
                    probes_sent = int(sent_and_received.groups()[0])
                    probes_received = int(sent_and_received.groups()[1])
                    ping_dict['success']['probes_sent'] = probes_sent
                    ping_dict['success']['packet_loss'] = probes_sent - probes_received
                elif 'Success rate is' in line:
                    sent_and_received = re.search(r'\((\d*)/(\d*)\)', fields[5])
                    probes_sent = int(sent_and_received.groups()[0])
                    probes_received = int(sent_and_received.groups()[1])
                    min_avg_max = re.search(r'(\d*)/(\d*)/(\d*)', fields[9])
                    ping_dict['success']['probes_sent'] = probes_sent
                    ping_dict['success']['packet_loss'] = probes_sent - probes_received
                    ping_dict['success'].update({
                        'rtt_min': float(min_avg_max.groups()[0]),
                        'rtt_avg': float(min_avg_max.groups()[1]),
                        'rtt_max': float(min_avg_max.groups()[2]),
                    })
                    results_array = []
                    for _ in range(probes_received):
                        results_array.append({'ip_address': py23_compat.text_type(destination),
                                              'rtt': 0.0})
                    ping_dict['success'].update({'results': results_array})

        if vrf:
            # change back to the default context if we've changed away
            if self.context and self.context != 'system':
                self.device.send_command("changeto context " + self.context)
            elif self.context:
                self.device.send_command("changeto system")
        return ping_dict

    def get_interfaces(self):
        """
        Get interface details.
        last_flapped is not implemented
        Example Output:
        {   u'Management0/0': {   'description': u'N/A',
                      'is_enabled': True,
                      'is_up': True,
                      'last_flapped': -1.0,
                      'mac_address': u'a493.4cc1.67a7',
                      'speed': 1000},
        u'GigabitEthernet0/0': {   'description': u'Data Network',
                        'is_enabled': True,
                        'is_up': True,
                        'last_flapped': -1.0,
                        'mac_address': u'a493.4cc1.67a7',
                        'speed': 1000},
        u'GigabitEthernet0/1': {   'description': u'Voice Network',
                        'is_enabled': True,
                        'is_up': True,
                        'last_flapped': -1.0,
                        'mac_address': u'a493.4cc1.67a7',
                        'speed': 1000}}
        """
        # default values.
        last_flapped = -1.0

        command = 'show interface'
        output = self._send_command(command)

        interface = description = mac_address = speed = speedformat = ''
        is_enabled = is_up = None

        interface_dict = {}
        for line in output.splitlines():

            interface_regex = \
                r"^Interface\s+(\S+?)\s+\"(\S*)\",\s+is\s+(.+?),\s+line\s+protocol\s+is\s+(\S+)"
            if re.search(interface_regex, line):
                interface_match = re.search(interface_regex, line)
                interface = interface_match.groups()[0]
                description = interface_match.groups()[1]
                status = interface_match.groups()[2]
                protocol = interface_match.groups()[3]

                if 'admin' in status:
                    is_enabled = False
                else:
                    is_enabled = True
                is_up = bool('up' in protocol)

            speed_regex = r"^\s+.+BW\s+(\d+)\s+([KMG]?b)"
            if re.search(speed_regex, line):
                speed_match = re.search(speed_regex, line)
                speed = speed_match.groups()[0]
                speedformat = speed_match.groups()[1]
                speed = float(speed)
                if speedformat.startswith('Kb'):
                    speed = speed / 1000.0
                elif speedformat.startswith('Gb'):
                    speed = speed * 1000
                speed = int(round(speed))

            vlan_regex = r"^\s+VLAN identifier"
            if re.search(vlan_regex, line):
                interface_dict[interface] = {'is_enabled': is_enabled, 'is_up': is_up,
                                             'description': description, 'mac_address': mac_address,
                                             'last_flapped': last_flapped, 'speed': speed}
                interface = description = mac_address = speed = speedformat = ''
                is_enabled = is_up = None

            mac_addr_regex = r"^\s+MAC\s+address\s+({})".format(MAC_REGEX)
            if re.search(mac_addr_regex, line):
                mac_addr_match = re.search(mac_addr_regex, line)
                mac_address = mac(mac_addr_match.groups()[0])

                if interface == '':
                    raise ValueError("Interface attributes were \
                                                  found without any known interface")
                if not isinstance(is_up, bool) or not isinstance(is_enabled, bool):
                    raise ValueError("Did not correctly find the interface status")

                interface_dict[interface] = {'is_enabled': is_enabled, 'is_up': is_up,
                                             'description': description, 'mac_address': mac_address,
                                             'last_flapped': last_flapped, 'speed': speed}
                interface = description = mac_address = speed = speedformat = ''
                is_enabled = is_up = None

        return interface_dict
