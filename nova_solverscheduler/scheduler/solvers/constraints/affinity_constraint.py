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

from nova.scheduler.filters import affinity_filter
from nova_solverscheduler.scheduler.solvers import constraints


class SameHostConstraint(constraints.BaseFilterConstraint):
    """Schedule the instance on the same host as another instance in a set
    of instances.
    """
    host_filter_cls = affinity_filter.SameHostFilter


class DifferentHostConstraint(constraints.BaseFilterConstraint):
    """Schedule the instance on a different host from a set of instances."""
    host_filter_cls = affinity_filter.DifferentHostFilter


class SimpleCidrAffinityConstraint(constraints.BaseFilterConstraint):
    """Schedule the instance on a host with a particular cidr."""
    host_filter_cls = affinity_filter.SimpleCIDRAffinityFilter
