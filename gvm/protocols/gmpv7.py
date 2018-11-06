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
Module for communication with gvmd in Greenbone Management Protocol version 7
"""
import logging

from lxml import etree

from gvm.errors import InvalidArgument, RequiredArgument
from gvm.utils import get_version_string
from gvm.xml import _GmpCommandFactory as GmpCommandFactory, XmlCommand

from .base import GvmProtocol

logger = logging.getLogger(__name__)

PROTOCOL_VERSION = (7,)

FILTER_TYPES = [
    'agent',
    'alert',
    'asset',
    'config',
    'credential',
    'filter',
    'group',
    'note',
    'override',
    'permission',
    'port_list',
    'report',
    'report_format',
    'result',
    'role',
    'schedule',
    'secinfo',
    'tag',
    'target',
    'task',
    'user',
]


def _check_command_status(xml):
    """Check gmp response

    Look into the gmp response and check for the status in the root element

    Arguments:
        xml {string} -- XML-Source

    Returns:
        bool -- True if valid, otherwise False
    """

    if xml is 0 or xml is None:
        logger.error('XML Command is empty')
        return False

    try:
        parser = etree.XMLParser(encoding='utf-8', recover=True)

        root = etree.XML(xml, parser=parser)
        status = root.attrib['status']
        return status is not None and status[0] == '2'

    except etree.Error as e:
        logger.error('etree.XML(xml): %s', e)
        return False


class Gmp(GvmProtocol):
    """Python interface for Greenbone Management Protocol

    This class implements the `Greenbone Management Protocol version 7`_

    Attributes:
        connection (:class:`gvm.connections.GvmConnection`): Connection to use
            to talk with the gvmd daemon. See :mod:`gvm.connections` for
            possible connection types.
        transform (`callable`_, optional): Optional transform callable to
            convert response data. After each request the callable gets passed
            the plain response data which can be used to check the data and/or
            conversion into different representaitions like a xml dom.

            See :mod:`gvm.transforms` for existing transforms.

    .. _Greenbone Management Protocol version 7:
        https://docs.greenbone.net/API/GMP/gmp-7.0.html
    .. _callable:
        https://docs.python.org/3.6/library/functions.html#callable
    """

    def __init__(self, connection, transform=None):
        super().__init__(connection, transform)

        # Is authenticated on gvmd
        self._authenticated = False

        # GMP Message Creator
        self._generator = GmpCommandFactory()

    @staticmethod
    def get_protocol_version():
        """Allow to determine the Greenbone Management Protocol version.

            Returns:
                str: Implemented version of the Greenbone Management Protocol
        """
        return get_version_string(PROTOCOL_VERSION)

    def is_authenticated(self):
        """Checks if the user is authenticated

        If the user is authenticated privilged GMP commands like get_tasks
        may be send to gvmd.

        Returns:
            bool: True if an authenticated connection to gvmd has been
            established.
        """
        return self._authenticated

    def authenticate(self, username, password):
        """Authenticate to gvmd.

        The generated authenticate command will be send to server.
        Afterwards the response is read, transformed and returned.

        Arguments:
            username (str): Username
            password (str): Password

        Returns:
            any, str by default: Transformed response from server.
        """
        cmd = XmlCommand('authenticate')

        if not username:
            raise RequiredArgument('authenticate requires username')

        if not password:
            raise RequiredArgument('authenticate requires password')

        credentials = cmd.add_element('credentials')
        credentials.add_element('username', username)
        credentials.add_element('password', password)

        self._send(cmd.to_string())
        response = self._read()

        if _check_command_status(response):
            self._authenticated = True

        return self._transform(response)

    def create_agent(self, installer, signature, name, comment=None, copy=None,
                     howto_install=None, howto_use=None):
        """Create a new agent

        Arguments:
            installer (str): A base64 encoded file that installs the agent on a
                target machine
            signature: (str): A detached OpenPGP signature of the installer
            name (str): A name for the agent
            comment (str, optional): A comment for the agent
            copy (str, optional): UUID of an existing agent to clone from
            howto_install (str, optional): A file that describes how to install
                the agent
            howto_user (str, optional): A file that describes how to use the
                agent
        """
        if not name:
            raise RequiredArgument('create_agent requires name argument')

        if not installer:
            raise RequiredArgument('create_agent requires installer argument')

        if not signature:
            raise RequiredArgument('create_agent requires signature argument')

        cmd = XmlCommand('create_agent')
        cmd.add_element('installer', installer)
        cmd.add_element('signature', signature)
        cmd.add_element('name', name)

        if comment:
            cmd.add_element('comment', comment)

        if copy:
            cmd.add_element('copy', copy)

        if howto_install:
            cmd.add_element('howto_install', howto_install)

        if howto_use:
            cmd.add_element('howto_use', howto_use)

        return self._send_xml_command(cmd)

    def create_alert(self, name, condition, event, method, filter_id='',
                     copy='', comment=''):
        cmd = self._generator.create_alert_command(name, condition, event,
                                                   method, filter_id, copy,
                                                   comment)
        return self.send_command(cmd)

    def create_asset(self, name, asset_type, comment=''):
        # TODO: Add the missing second method. Also the docs are not complete!
        cmd = self._generator.create_asset_command(name, asset_type, comment)
        return self.send_command(cmd)

    def create_config(self, copy_id, name):
        cmd = self._generator.create_config_command(copy_id, name)
        return self.send_command(cmd)

    def create_credential(self, name, **kwargs):
        cmd = self._generator.create_credential_command(name, kwargs)
        return self.send_command(cmd)

    def create_filter(self, name, make_unique=False, filter_type=None,
                      comment=None, term=None, copy=None):
        """Create a new filter

        Arguments:
            name (str): Name of the new filter
            make_unique (boolean, optional):
            filter_type (str, optional): Filter for entity type
            comment (str, optional): Comment for the filter
            term (str, optional): Filter term e.g. 'name=foo'
            copy (str, optional): UUID of an existing filter

        Returns:
            The response. See :py:meth:`send_command` for details.
        """
        if not name:
            raise RequiredArgument('create_filter requires a name argument')

        cmd = XmlCommand('create_filter')
        _xmlname = cmd.add_element('name', name)
        if make_unique:
            _xmlname.add_element('make_unique', '1')

        if comment:
            cmd.add_element('comment', comment)

        # TODO: Move copy into an extra method
        if copy:
            cmd.add_element('copy', copy)

        if term:
            cmd.add_element('term', term)

        if filter_type:
            filter_type = filter_type.lower()
            if filter_type not in FILTER_TYPES:
                raise InvalidArgument(
                    'create_filter requires type to be one of {0} but '
                    'was {1}'.format(', '.join(FILTER_TYPES), filter_type))
            cmd.add_element('type', filter_type)

        return self._send_xml_command(cmd)

    def create_group(self, name, **kwargs):
        cmd = self._generator.create_group_command(name, kwargs)
        return self.send_command(cmd)

    # TODO: Create notes with comment returns bogus element. Research
    def create_note(self, text, nvt_oid, **kwargs):
        cmd = self._generator.create_note_command(text, nvt_oid, kwargs)
        return self.send_command(cmd)

    def create_override(self, text, nvt_oid, **kwargs):
        cmd = self._generator.create_override_command(text, nvt_oid, kwargs)
        return self.send_command(cmd)

    def create_permission(self, name, subject_id, permission_type, **kwargs):
        cmd = self._generator.create_permission_command(
            name, subject_id, permission_type, kwargs)
        return self.send_command(cmd)

    def create_port_list(self, name, port_range, **kwargs):
        cmd = self._generator.create_port_list_command(name, port_range, kwargs)
        return self.send_command(cmd)

    def create_port_range(self, port_list_id, start, end, port_range_type,
                          comment=''):
        cmd = self._generator.create_port_range_command(
            port_list_id, start, end, port_range_type, comment)
        return self.send_command(cmd)

    def create_report(self, report_xml_string, **kwargs):
        cmd = self._generator.create_report_command(report_xml_string, kwargs)
        return self.send_command(cmd)

    def create_role(self, name, **kwargs):
        cmd = self._generator.create_role_command(name, kwargs)
        return self.send_command(cmd)

    def create_scanner(self, name, host, port, scanner_type, ca_pub,
                       credential_id, **kwargs):
        cmd = self._generator.create_scanner_command(name, host, port,
                                                     scanner_type, ca_pub,
                                                     credential_id, kwargs)
        return self.send_command(cmd)

    def create_schedule(self, name, **kwargs):
        cmd = self._generator.create_schedule_command(name, kwargs)
        return self.send_command(cmd)

    def create_tag(self, name, resource_id, resource_type, **kwargs):
        cmd = self._generator.create_tag_command(name, resource_id,
                                                 resource_type, kwargs)
        return self.send_command(cmd)

    def create_target(self, name, make_unique=False, asset_hosts_filter=None,
                      hosts=None, comment=None, copy=None, exclude_hosts=None,
                      ssh_credential_id=None, ssh_credential_port=None,
                      smb_credential_id=None, esxi_credential_id=None,
                      snmp_credential_id=None, alive_tests=None,
                      reverse_lookup_only=None, reverse_lookup_unify=None,
                      port_range=None, port_list_id=None):
        """Create a new target

        Arguments:
            name (str): Name of the target
            make_unique (boolean, optional): Append a unique suffix if the name
                already exists
            asset_hosts_filter (str, optional): Filter to select target host
                from assets hosts
            hosts (str, optional): Hosts to scan
            exclude_hosts (str, optional): Hosts to exclude from scan
            comment (str, optional): Comment for the target
            copy (str, optional): UUID of an existing target to clone from
            ssh_credential_id (str, optional): UUID of a ssh credential to use
                on target
            ssh_credential_port (str, optional): The port to use for ssh
                credential
            smb_credential_id (str, optional): UUID of a smb credential to use
                on target
            snmp_credential_id (str, optional): UUID of a snmp credential to use
                on target
            esxi_credential_id (str, optional): UUID of a esxi credential to use
                on target
            alive_tests (str, optional): Which alive tests to use
            reverse_lookup_only (boolean, optional): Whether to scan only hosts
                that have names
            reverse_lookup_unify (boolean, optional): Whether to scan only one
                IP when multiple IPs have the same name.
            port_range (str, optional): Port range for the target
            port_list_id (str, optional): UUID of the port list to use on target

        Returns:
            The response. See :py:meth:`send_command` for details.
        """
        if not name:
            raise RequiredArgument('create_target requires a name argument')

        cmd = XmlCommand('create_target')
        _xmlname = cmd.add_element('name', name)
        if make_unique:
            _xmlname.add_element('make_unique', '1')

        if asset_hosts_filter:
            cmd.add_element('asset_hosts',
                            attrs={'filter': str(asset_hosts_filter)})
        elif hosts:
            cmd.add_element('hosts', hosts)
        else:
            raise RequiredArgument('create_target requires either a hosts or '
                                   'an asset_hosts_filter argument')

        if comment:
            cmd.add_element('comment', comment)

        if copy:
            # TODO move copy case into clone_target method

            # NOTE: It seems that hosts/asset_hosts is silently ignored by the
            # server when copy is supplied. But for specification conformance
            # we raise the ValueError above and consider copy optional.
            cmd.add_element('copy', copy)

        if exclude_hosts:
            cmd.add_element('exclude_hosts', exclude_hosts)

        if ssh_credential_id:
            _xmlssh = cmd.add_element('ssh_credential',
                                      attrs={'id': ssh_credential_id})
            if ssh_credential_port:
                _xmlssh.add_element('port', ssh_credential_port)

        if smb_credential_id:
            cmd.add_element('smb_credential', attrs={'id': smb_credential_id})

        if esxi_credential_id:
            cmd.add_element('esxi_credential', attrs={'id': esxi_credential_id})

        if snmp_credential_id:
            cmd.add_element('snmp_credential', attrs={'id': snmp_credential_id})

        if alive_tests:
            cmd.add_element('alive_tests', alive_tests)

        if not reverse_lookup_only is None:
            if reverse_lookup_only:
                cmd.add_element('reverse_lookup_only', '1')
            else:
                cmd.add_element('reverse_lookup_only', '0')

        if not reverse_lookup_unify is None:
            if reverse_lookup_unify:
                cmd.add_element('reverse_lookup_unify', '1')
            else:
                cmd.add_element('reverse_lookup_unify', '0')

        if port_range:
            cmd.add_element('port_range', port_range)

        if port_list_id:
            cmd.add_element('port_list', attrs={'id': port_list_id})

        return self._send_xml_command(cmd)

    def create_task(self, name, config_id, target_id, scanner_id,
                    alert_ids=None, comment=''):
        if alert_ids is None:
            alert_ids = []
        cmd = self._generator.create_task_command(
            name, config_id, target_id, scanner_id, alert_ids, comment)
        return self.send_command(cmd)

    def create_user(self, name, password, copy='', hosts_allow='0',
                    ifaces_allow='0', role_ids=(), hosts=None, ifaces=None):
        cmd = self._generator.create_user_command(
            name, password, copy, hosts_allow, ifaces_allow, role_ids, hosts,
            ifaces)
        return self.send_command(cmd)

    def delete_agent(self, **kwargs):
        cmd = self._generator.delete_agent_command(kwargs)
        return self.send_command(cmd)

    def delete_alert(self, **kwargs):
        cmd = self._generator.delete_alert_command(kwargs)
        return self.send_command(cmd)

    def delete_asset(self, asset_id, ultimate=0):
        cmd = self._generator.delete_asset_command(asset_id, ultimate)
        return self.send_command(cmd)

    def delete_config(self, config_id, ultimate=0):
        cmd = self._generator.delete_config_command(config_id, ultimate)
        return self.send_command(cmd)

    def delete_credential(self, credential_id, ultimate=0):
        cmd = self._generator.delete_credential_command(credential_id, ultimate)
        return self.send_command(cmd)

    def delete_filter(self, filter_id, ultimate=0):
        cmd = self._generator.delete_filter_command(filter_id, ultimate)
        return self.send_command(cmd)

    def delete_group(self, group_id, ultimate=0):
        cmd = self._generator.delete_group_command(group_id, ultimate)
        return self.send_command(cmd)

    def delete_note(self, note_id, ultimate=0):
        cmd = self._generator.delete_note_command(note_id, ultimate)
        return self.send_command(cmd)

    def delete_override(self, override_id, ultimate=0):
        cmd = self._generator.delete_override_command(override_id, ultimate)
        return self.send_command(cmd)

    def delete_permission(self, permission_id, ultimate=0):
        cmd = self._generator.delete_permission_command(permission_id, ultimate)
        return self.send_command(cmd)

    def delete_port_list(self, port_list_id, ultimate=0):
        cmd = self._generator.delete_port_list_command(port_list_id, ultimate)
        return self.send_command(cmd)

    def delete_port_range(self, port_range_id):
        cmd = self._generator.delete_port_range_command(port_range_id)
        return self.send_command(cmd)

    def delete_report(self, report_id):
        cmd = self._generator.delete_report_command(report_id)
        return self.send_command(cmd)

    def delete_report_format(self, report_format_id, ultimate=0):
        cmd = self._generator.delete_report_format_command(
            report_format_id, ultimate)
        return self.send_command(cmd)

    def delete_role(self, role_id, ultimate=0):
        cmd = self._generator.delete_role_command(role_id, ultimate)
        return self.send_command(cmd)

    def delete_scanner(self, scanner_id, ultimate=0):
        cmd = self._generator.delete_scanner_command(scanner_id, ultimate)
        return self.send_command(cmd)

    def delete_schedule(self, schedule_id, ultimate=0):
        cmd = self._generator.delete_schedule_command(schedule_id, ultimate)
        return self.send_command(cmd)

    def delete_tag(self, tag_id, ultimate=0):
        cmd = self._generator.delete_tag_command(tag_id, ultimate)
        return self.send_command(cmd)

    def delete_target(self, target_id, ultimate=0):
        cmd = self._generator.delete_target_command(target_id, ultimate)
        return self.send_command(cmd)

    def delete_task(self, task_id, ultimate=0):
        cmd = self._generator.delete_task_command(task_id, ultimate)
        return self.send_command(cmd)

    def delete_user(self, **kwargs):
        cmd = self._generator.delete_user_command(kwargs)
        return self.send_command(cmd)

    def describe_auth(self):
        cmd = self._generator.describe_auth_command()
        return self.send_command(cmd)

    def empty_trashcan(self):
        cmd = self._generator.empty_trashcan_command()
        return self.send_command(cmd)

    def get_agents(self, **kwargs):
        cmd = self._generator.get_agents_command(kwargs)
        return self.send_command(cmd)

    def get_aggregates(self, **kwargs):
        cmd = self._generator.get_aggregates_command(kwargs)
        return self.send_command(cmd)

    def get_alerts(self, **kwargs):
        cmd = self._generator.get_alerts_command(kwargs)
        return self.send_command(cmd)

    def get_assets(self, **kwargs):
        cmd = self._generator.get_assets_command(kwargs)
        return self.send_command(cmd)

    def get_credentials(self, **kwargs):
        cmd = self._generator.get_credentials_command(kwargs)
        return self.send_command(cmd)

    def get_configs(self, **kwargs):
        cmd = self._generator.get_configs_command(kwargs)
        return self.send_command(cmd)

    def get_feeds(self, **kwargs):
        cmd = self._generator.get_feeds_command(kwargs)
        return self.send_command(cmd)

    def get_filters(self, **kwargs):
        cmd = self._generator.get_filters_command(kwargs)
        return self.send_command(cmd)

    def get_groups(self, **kwargs):
        cmd = self._generator.get_groups_command(kwargs)
        return self.send_command(cmd)

    def get_info(self, **kwargs):
        cmd = self._generator.get_info_command(kwargs)
        return self.send_command(cmd)

    def get_notes(self, **kwargs):
        cmd = self._generator.get_notes_command(kwargs)
        return self.send_command(cmd)

    def get_nvts(self, **kwargs):
        cmd = self._generator.get_nvts_command(kwargs)
        return self.send_command(cmd)

    def get_nvt_families(self, **kwargs):
        cmd = self._generator.get_nvt_families_command(kwargs)
        return self.send_command(cmd)

    def get_overrides(self, **kwargs):
        cmd = self._generator.get_overrides_command(kwargs)
        return self.send_command(cmd)

    def get_permissions(self, **kwargs):
        cmd = self._generator.get_permissions_command(kwargs)
        return self.send_command(cmd)

    def get_port_lists(self, **kwargs):
        cmd = self._generator.get_port_lists_command(kwargs)
        return self.send_command(cmd)

    def get_preferences(self, **kwargs):
        cmd = self._generator.get_preferences_command(kwargs)
        return self.send_command(cmd)

    def get_reports(self, **kwargs):
        cmd = self._generator.get_reports_command(kwargs)
        return self.send_command(cmd)

    def get_report_formats(self, **kwargs):
        cmd = self._generator.get_report_formats_command(kwargs)
        return self.send_command(cmd)

    def get_results(self, **kwargs):
        cmd = self._generator.get_results_command(kwargs)
        return self.send_command(cmd)

    def get_roles(self, **kwargs):
        cmd = self._generator.get_roles_command(kwargs)
        return self.send_command(cmd)

    def get_scanners(self, **kwargs):
        cmd = self._generator.get_scanners_command(kwargs)
        return self.send_command(cmd)

    def get_schedules(self, **kwargs):
        cmd = self._generator.get_schedules_command(kwargs)
        return self.send_command(cmd)

    def get_settings(self, **kwargs):
        cmd = self._generator.get_settings_command(kwargs)
        return self.send_command(cmd)

    def get_system_reports(self, **kwargs):
        cmd = self._generator.get_system_reports_command(kwargs)
        return self.send_command(cmd)

    def get_tags(self, **kwargs):
        cmd = self._generator.get_tags_command(kwargs)
        return self.send_command(cmd)

    def get_targets(self, **kwargs):
        cmd = self._generator.get_targets_command(kwargs)
        return self.send_command(cmd)

    def get_tasks(self, **kwargs):
        cmd = self._generator.get_tasks_command(kwargs)
        return self.send_command(cmd)

    def get_users(self, **kwargs):
        cmd = self._generator.get_users_command(kwargs)
        return self.send_command(cmd)

    def get_version(self):
        cmd = self._generator.get_version_command()
        return self.send_command(cmd)

    def help(self, **kwargs):
        cmd = self._generator.help_command(kwargs)
        return self.send_command(cmd)

    def modify_agent(self, agent_id, name='', comment=''):
        cmd = self._generator.modify_agent_command(agent_id, name, comment)
        return self.send_command(cmd)

    def modify_alert(self, alert_id, **kwargs):
        cmd = self._generator.modify_alert_command(alert_id, kwargs)
        return self.send_command(cmd)

    def modify_asset(self, asset_id, comment):
        cmd = self._generator.modify_asset_command(asset_id, comment)
        return self.send_command(cmd)

    def modify_auth(self, group_name, auth_conf_settings):
        cmd = self._generator.modify_auth_command(group_name,
                                                  auth_conf_settings)
        return self.send_command(cmd)

    def modify_config(self, selection, **kwargs):
        cmd = self._generator.modify_config_command(selection, kwargs)
        return self.send_command(cmd)

    def modify_credential(self, credential_id, **kwargs):
        cmd = self._generator.modify_credential_command(
            credential_id, kwargs)
        return self.send_command(cmd)

    def modify_filter(self, filter_id, **kwargs):
        cmd = self._generator.modify_filter_command(filter_id, kwargs)
        return self.send_command(cmd)

    def modify_group(self, group_id, **kwargs):
        cmd = self._generator.modify_group_command(group_id, kwargs)
        return self.send_command(cmd)

    def modify_note(self, note_id, text, **kwargs):
        cmd = self._generator.modify_note_command(note_id, text, kwargs)
        return self.send_command(cmd)

    def modify_override(self, override_id, text, **kwargs):
        cmd = self._generator.modify_override_command(override_id, text,
                                                      kwargs)
        return self.send_command(cmd)

    def modify_permission(self, permission_id, **kwargs):
        cmd = self._generator.modify_permission_command(
            permission_id, kwargs)
        return self.send_command(cmd)

    def modify_port_list(self, port_list_id, **kwargs):
        cmd = self._generator.modify_port_list_command(port_list_id, kwargs)
        return self.send_command(cmd)

    def modify_report(self, report_id, comment):
        cmd = self._generator.modify_report_format_command(report_id, comment)
        return self.send_command(cmd)

    def modify_report_format(self, report_format_id, **kwargs):
        cmd = self._generator.modify_report_format_command(report_format_id,
                                                           kwargs)
        return self.send_command(cmd)

    def modify_role(self, role_id, **kwargs):
        cmd = self._generator.modify_role_command(role_id, kwargs)
        return self.send_command(cmd)

    def modify_scanner(self, scanner_id, host, port, scanner_type, **kwargs):
        cmd = self._generator.modify_scanner_command(scanner_id, host, port,
                                                     scanner_type, kwargs)
        return self.send_command(cmd)

    def modify_schedule(self, schedule_id, **kwargs):
        cmd = self._generator.modify_schedule_command(schedule_id, kwargs)
        return self.send_command(cmd)

    def modify_setting(self, setting_id, name, value):
        cmd = self._generator.modify_setting_command(setting_id, name, value)
        return self.send_command(cmd)

    def modify_tag(self, tag_id, **kwargs):
        cmd = self._generator.modify_tag_command(tag_id, kwargs)
        return self.send_command(cmd)

    def modify_target(self, target_id, **kwargs):
        cmd = self._generator.modify_target_command(target_id, kwargs)
        return self.send_command(cmd)

    def modify_task(self, task_id, **kwargs):
        cmd = self._generator.modify_task_command(task_id, kwargs)
        return self.send_command(cmd)

    def modify_user(self, **kwargs):
        cmd = self._generator.modify_user_command(kwargs)
        return self.send_command(cmd)

    def move_task(self, task_id, slave_id):
        cmd = self._generator.move_task_command(task_id, slave_id)
        return self.send_command(cmd)

    def restore(self, entity_id):
        cmd = self._generator.restore_command(entity_id)
        return self.send_command(cmd)

    def resume_task(self, task_id):
        cmd = self._generator.resume_task_command(task_id)
        return self.send_command(cmd)

    def start_task(self, task_id):
        cmd = self._generator.start_task_command(task_id)
        return self.send_command(cmd)

    def stop_task(self, task_id):
        cmd = self._generator.stop_task_command(task_id)
        return self.send_command(cmd)

    def sync_cert(self):
        cmd = self._generator.sync_cert_command()
        return self.send_command(cmd)

    def sync_config(self):
        cmd = self._generator.sync_config_command()
        return self.send_command(cmd)

    def sync_feed(self):
        cmd = self._generator.sync_feed_command()
        return self.send_command(cmd)

    def sync_scap(self):
        cmd = self._generator.sync_scap_command()
        return self.send_command(cmd)

    def test_alert(self, alert_id):
        cmd = self._generator.test_alert_command(alert_id)
        return self.send_command(cmd)

    def verify_agent(self, agent_id):
        cmd = self._generator.verify_agent_command(agent_id)
        return self.send_command(cmd)

    def verify_report_format(self, report_format_id):
        cmd = self._generator.verify_report_format_command(report_format_id)
        return self.send_command(cmd)

    def verify_scanner(self, scanner_id):
        cmd = self._generator.verify_scanner_command(scanner_id)
        return self.send_command(cmd)
