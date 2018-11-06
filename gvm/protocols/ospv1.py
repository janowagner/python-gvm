# -*- coding: utf-8 -*-
# Copyright (C) 2018 Greenbone Networks GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Module for communication to a daemon speaking Open Scanner Protocol version 1
"""
import logging

from gvm.errors import RequiredArgument
from gvm.utils import get_version_string
from gvm.xml import XmlCommand

from .base import GvmProtocol

logger = logging.getLogger(__name__)

PROTOCOL_VERSION = (1, 2,)


def create_credentials_element(_xmlcredentials, credentials):
    """Generates an xml element with credentials."""
    for service, credential in credentials.items():
        cred_type = credential.get('type')
        serv_port = credential.get('port')
        username = credential.get('username')
        password = credential.get('password')
        _xmlcredential = _xmlcredentials.add_element(
            'credential', attrs={
                'type': cred_type,
                'port': serv_port,
                'service': service,
            })
        _xmlcredential.add_element('username', username)
        _xmlcredential.add_element('password', password)
    return _xmlcredentials

def create_vt_selection_element(_xmlvtselection, vt_selection):
    """Generates an xml element with a selection of Vulnerability tests."""
    for vt_id, vt_values in vt_selection.items():
        if vt_id != 'vt_groups':
            _xmlvt = _xmlvtselection.add_element('vt_single',
                                                 attrs={'id': vt_id})
            if vt_values:
                for key, value in vt_values.items():
                    _xmlvt.add_element('vt_value', value, attrs={'id': key})
        else:
            for group in vt_values:
                _xmlvt = _xmlvtselection.add_element(
                    'vt_group', attrs={'filter': group})

    return _xmlvtselection

class Osp(GvmProtocol):

    @staticmethod
    def get_protocol_version():
        """Allow to determine the Open Scanner Protocol version.

            Returns:
                str: Implemented version of the Open Scanner Protocol
        """
        return get_version_string(PROTOCOL_VERSION)

    def get_version(self):
        """Get the version of the OSPD server which is connected to."""
        cmd = XmlCommand('get_version')
        return self.send_command(cmd.to_string())

    def help(self):
        """Get the help text."""
        cmd = XmlCommand('help')
        return self.send_command(cmd.to_string())

    def get_scans(self, scan_id=None, details=True, pop_results=False):
        """Get the stored scans.

         Args:
            scan_id (uuid): Identifier for a scan.
            details (boolean): Whether to get full scan reports.
            pop_results (boolean) Whether to remove the fetched results.

        Returns:
            str: Response from server.
        """
        cmd = XmlCommand('get_scans')
        if scan_id:
            cmd.set_attribute('scan_id', scan_id)
        if details:
            cmd.set_attribute('details', '1')
        else:
            cmd.set_attribute('details', '0')

        if pop_results:
            cmd.set_attribute('pop_results', '1')
        else:
            cmd.set_attribute('pop_results', '0')

        return self.send_command(cmd.to_string())

    def delete_scan(self, scan_id=None):
        """Delete a finished scan.
        Args:
            scan_id (uuid): Identifier for a finished scan.
        Returns:
            str: Response from server.
        """
        if not scan_id:
            raise ValueError('delete_scan requires a scan_id element')
        cmd = XmlCommand('delete_scan')
        cmd.set_attribute('scan_id', scan_id)

        return self.send_command(cmd.to_string())

    def get_scanner_details(self):
        """Return scanner description and parameters."""
        cmd = XmlCommand('get_scanner_details')
        return self.send_command(cmd.to_string())

    def get_vts(self, vt_id=None):
        """Return information about vulnerability tests,
        if offered by scanner.

        Args:
            vt_id (uuid): Identifier for a vulnerability test.
        Returns:
            str: Response from server.
        """
        cmd = XmlCommand('get_vts')
        if vt_id:
            cmd.set_attribute('vt_id', vt_id)

        return self.send_command(cmd.to_string())

    def start_scan(self, scan_id=None, parallel=1, target=None,
                   ports=None, targets=None, scanner_params=None,
                   vt_selection=None):
        """Start a new scan.

        Args:
            scan_id (uuid, optinal): Identifier for a running scan.
            parallel (int, optional): Number of parallel scanned targets.
                Default 1.
            target (dict, optional): Deprecated. Please use targets instead.
            targets (list, optional): List of dictionaries. See example.
            ports (str, optional): Deprecated. Ports to use for target
                parameter.
            scanner_params: (dict, optional): Dictionary of scanner parameters.
            vt_selection: (dict, optional): Vulnerability tests to select. See
                example.

        Returns:
            str: Response from server.


        Examples:

            Scanner Paramters::

                scanner_parameters = {
                    'scan_param1': 'scan_param1_value',
                    'scan_param2': 'scan_param2_value',
                }

            Targets::

                targets = [{
                    'hosts': 'localhost',
                    'ports': '80,43'
                }, {
                    'hosts': '192.168.0.0/24',
                    'ports': '22',
                }, {
                    'credentials': {
                        'smb': {
                            'password': 'pass',
                            'port': 'port',
                            'type': 'type',
                            'username': 'username',
                        }
                    }
                }]

            VT Selection::

                vt_selection = {
                    'vt1': {},
                    'vt2': {'value_id': 'value'},
                    'vt_groups': ['family=debian', 'family=general']
                }
        """
        cmd = XmlCommand('start_scan')

        if scan_id:
            cmd.set_attribute('scan_id', scan_id)

        cmd.set_attribute('parallel', str(parallel))

        # Add <scanner_params> even if it is empty, since it is mandatory
        _xmlscanparams = cmd.add_element('scanner_params')
        if scanner_params:
            _xmlscanparams.set_attributes(scanner_params)

        if targets:
            _xmltargets = cmd.add_element('targets')
            for target in targets:
                _xmltarget = _xmltargets.add_element('target')
                hosts = target.get('hosts')
                ports = target.get('ports')
                credentials = target.get('credentials')
                _xmltarget.add_element('hosts', hosts)
                _xmltarget.add_element('ports', ports)
                if credentials:
                    _xmlcredentials = _xmltarget.add_element('credentials')
                    _xmlcredentials = (create_credentials_element(
                        _xmlcredentials, credentials))
        # Check target as attribute for legacy mode compatibility. Deprecated.
        elif target:
            cmd.set_attribute('target', target)
            if ports:
                cmd.set_attribute('ports', ports)
        else:
            raise RequiredArgument('start_scan requires a target. Please pass '
                                   'targets parameter.')

        if vt_selection:
            _xmlvtselection = cmd.add_element('vt_selection')
            _xmlvtselection = create_vt_selection_element(
                _xmlvtselection, vt_selection)

        return self.send_command(cmd.to_string())

    def stop_scan(self, scan_id=None):
        """Stop a currently running scan.

        Args:
            scan_id (uuid): Identifier for a running scan.
        Returns:
            str: Response from server.
        """
        if not scan_id:
            raise ValueError('stop_scan requires a scan_id element')
        cmd = XmlCommand('stop_scan')
        cmd.set_attribute('scan_id', scan_id)

        return self.send_command(cmd.to_string())
