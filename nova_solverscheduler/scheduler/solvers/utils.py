# Copyright 2015 Cisco Systems, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Utility methods for scheduler solvers."""

import os.path

from oslo_config import cfg
from oslo_log import log as logging

from nova.i18n import _LE

rack_config_file_opts = [
    cfg.StrOpt('rack_config',
            default='',
            help='The config file specifying physical rack configuration. By '
                 'default Cisco\'s Neutron ML2 plugin config is supported, '
                 'otherwise the format of the config file needs to be '
                 'compatible with Cisco\'s Neutron ML2 plugin config file.'),
    cfg.StrOpt('rack_config_prefix',
            default='',
            help='The section name in rack config file should start with the '
                 'prefix, so the config parser can recognize the section as '
                 'information of a specific rack or ToR switch. For example, '
                 'in Cisco\'s Neutron ML2 plugin config a section name like '
                 '[ml2_mech_cisco_nexus:1.1.1.1] identifies a specific ToR '
                 'switch, then the prefix is \'ml2_mech_cisco_nexus\'.')
]

CONF = cfg.CONF
CONF.register_opts(rack_config_file_opts)

LOG = logging.getLogger(__name__)


def get_host_racks_config():
        """Read the rack config file to get physical rack configurations."""
        # Example section in the file:
        # [ml2_mech_cisco_nexus:1.1.1.1]
        # compute1=1/1
        # compute2=1/2
        # ...

        host_racks_map = {}
        sections = {}

        filepath = CONF.rack_config
        if not filepath:
            return host_racks_map

        if not os.path.exists(filepath):
            LOG.error(_LE("The rack config file is not found: %s"), filepath)
            return host_racks_map

        prefix = CONF.rack_config_prefix
        if not prefix:
            LOG.error(_LE("Rack config prefix is not set."))
            return host_racks_map

        try:
            rack_config_parser = cfg.ConfigParser(filepath, sections)
            rack_config_parser.parse()

            for section_name in sections.keys():
                if section_name.startswith(prefix):
                    # section_name: rack id
                    for key, value in sections[section_name].items():
                        # key: host name, value: port id
                        host_racks_map.setdefault(key, set([]))
                        host_racks_map[key].add(section_name)
        except Exception as e:
            LOG.error(_LE("The rack config file is not parsed properly: %s"),
                      str(e))

        return host_racks_map
