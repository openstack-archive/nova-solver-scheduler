# Copyright (c) 2014 Cisco Systems Inc.
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

"""Volume affinity cost.
   This pluggable cost provides a way to schedule a VM on a host that has
   a specified volume.  In the cost matrix used for the linear programming
   optimization problem, the entries for the host that contains the
   specified volume is given as 0, and 1 for other hosts. So all the other
   hosts have equal cost and are considered equal. Currently this solution
   allows you to provide only one volume_id as a hint, so this solution
   works best for scheduling a single VM. Another limitation is that the
   user needs to have an admin context to obtain the host information from
   the cinderclient. Without the knowledge of the host containing the volume
   all hosts will have the same cost of 1.
"""

from cinderclient import exceptions as client_exceptions

from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
from nova.scheduler import driver as scheduler_driver
from nova.scheduler.solvers import costs as solvercosts
import nova.volume.cinder as volumecinder

LOG = logging.getLogger(__name__)


class VolumeAffinityCost(solvercosts.BaseCost):
    """The cost is 0 for same-as-volume host and 1 otherwise."""

    hint_name = 'affinity_volume_id'

    def get_cost_matrix(self, hosts, instance_uuids, request_spec,
                        filter_properties):
        num_hosts = len(hosts)
        if instance_uuids:
            num_instances = len(instance_uuids)
        else:
            num_instances = request_spec.get('num_instances', 1)

        context = filter_properties.get('context')
        scheduler_hints = filter_properties.get('scheduler_hints', None)

        cost_matrix = [[1.0 for j in range(num_instances)]
                       for i in range(num_hosts)]

        if scheduler_hints is not None:
            volume_id = scheduler_hints.get(self.hint_name, None)
            LOG.debug(_("volume id: %s") % volume_id)
            if volume_id:
                volume = None
                volume_host = None
                try:
                    volume = volumecinder.cinderclient(context).volumes.get(
                                 volume_id)
                    if volume:
                        volume = volumecinder.cinderadminclient().volumes.get(
                                    volume_id)
                        volume_host = getattr(volume, 'os-vol-host-attr:host',
                                        None)
                    LOG.debug(_("volume host: %s") % volume_host)
                except client_exceptions.NotFound:
                    LOG.warning(
                        _("volume with provided id ('%s') was not found")
                        % volume_id)
                except client_exceptions.Unauthorized:
                    LOG.warning(_("Failed to retrieve volume %s: unauthorized")
                        % volume_id)
                except:
                    LOG.warning(_("Failed to retrieve volume due to an error"))

                if volume_host:
                    for i in range(num_hosts):
                        host_state = hosts[i]
                        if host_state.host == volume_host:
                            cost_matrix[i] = [0.0
                                              for j in range(num_instances)]
                        LOG.debug(_("this host: %(h1)s volume host: %(h2)s") %
                                  {"h1": host_state.host, "h2": volume_host})
                else:
                    LOG.warning(_("Cannot find volume host."))
        return cost_matrix
