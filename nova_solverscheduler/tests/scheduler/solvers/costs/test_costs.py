# Copyright (c) 2014 Cisco Systems, Inc.
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

"""
Tests for solver scheduler costs.
"""

from nova import context
from nova import test
from nova_solverscheduler.scheduler.solvers import costs


class CostTestBase(test.NoDBTestCase):
    """Base test case for costs."""
    def setUp(self):
        super(CostTestBase, self).setUp()
        self.context = context.RequestContext('fake', 'fake')
        cost_handler = costs.CostHandler()
        classes = cost_handler.get_matching_classes(
                ['nova_solverscheduler.scheduler.solvers.costs.all_costs'])
        self.class_map = {}
        for c in classes:
            self.class_map[c.__name__] = c


class CostsTestCase(CostTestBase):
    def test_all_costs(self):
        """Test the existence of all cost classes."""
        self.assertIn('RamCost', self.class_map)
        self.assertIn('MetricsCost', self.class_map)

    def test_base_linear_costs(self):
        blc = costs.BaseLinearCost()
        variables, coefficients = blc.get_components(None, None, None)
        self.assertEqual([], variables)
        self.assertEqual([], coefficients)
