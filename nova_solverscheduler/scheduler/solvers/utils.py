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

from oslo.config import cfg

from nova import exception
from nova.objects import instance as instance_obj
from nova.objects import instance_group as instance_group_obj
from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging

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
        msg = _("The rack config file is not found: %s")
        LOG.error(msg % filepath)
        return host_racks_map

    prefix = CONF.rack_config_prefix
    if not prefix:
        msg = _("Rack config prefix is not set.")
        LOG.error(msg)
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
        msg = _("The rack config file is not parsed properly: %s")
        LOG.error(msg % str(e))

    return host_racks_map


def get_hosts_from_instance_uuids(context, uuids):
    """Get the hosts' names of the instances given in uuids.
    The uuids must be a list.
    """

    filters = {'uuid': uuids, 'deleted': False}
    instances = instance_obj.InstanceList.get_by_filters(context,
                                                         filters=filters)

    if len(instances) < len(uuids):
        missing_uuids = list(set(uuids) - set([instance.uuid for instance
                                               in instances if instance.uuid]))
        raise exception.InstanceNotFound(instance_id=', '.join(missing_uuids))

    hosts = set([])
    instances_invalid_host = []
    for instance in instances:
        if instance.host:
            hosts.add(instance.host)
        else:
            instances_invalid_host.append(instance.uuid)
    if instances_invalid_host:
        raise ValueError(_("Invalid host value for instance: %(insts)s")
                        % {'insts': ', '.join(instances_invalid_host)})

    hosts = list(hosts)

    return hosts


def get_hosts_from_group_hint(context, group_hint):
    """Get the instance hosts of the instance group given in group_hint.
    The group_hint must be a string of group uuid or name.
    """
    group = instance_group_obj.InstanceGroup.get_by_hint(context, group_hint)
    group_members = group.members or []
    hosts = get_hosts_from_instance_uuids(context, group_members)
    return hosts
