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

from nova.scheduler.filters import trusted_filter
from nova.scheduler.solvers import constraints


class TrustedHostsConstraint(constraints.BaseFilterConstraint):
    """Constraint to add support for Trusted Computing Pools.

    Allows a host to be selected by scheduler only when the integrity (trust)
    of that host matches the trust requested in the `extra_specs' for the
    flavor.  The `extra_specs' will contain a key/value pair where the
    key is `trust'.  The value of this pair (`trusted'/`untrusted') must
    match the integrity of that host (obtained from the Attestation
    service) before the task can be scheduled on that host.
    """
    host_filter_cls = trusted_filter.TrustedFilter
