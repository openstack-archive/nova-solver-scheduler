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

from nova.scheduler.solvers.costs import utils
from nova import test


class CostUtilsTestCase(test.NoDBTestCase):

    def test_normalize_cost_matrix(self):
        test_matrix = [
                [1, 2, 3, 4],
                [5, 7, 9, 10],
                [-2, -1, 0, 2]]

        expected_result = [
                [0.2, 0.4, 0.6, 0.8],
                [1.0, 1.4, 1.8, 2.0],
                [-0.4, -0.2, 0.0, 0.4]]

        result = utils.normalize_cost_matrix(test_matrix)

        round_values = lambda x: [round(v, 4) for v in x]
        expected_result = map(round_values, expected_result)
        result = map(round_values, result)

        self.assertEqual(expected_result, result)

    def test_normalize_cost_matrix_empty_input(self):
        test_matrix = []
        expected_result = []
        result = utils.normalize_cost_matrix(test_matrix)
        self.assertEqual(expected_result, result)

    def test_normalize_cost_matrix_first_column_all_zero(self):
        test_matrix = [
                [0, 1, 2, 3],
                [0, -1, -2, -3],
                [0, 0.2, 0.4, 0.6]]

        expected_result = [
                [0, 1, 2, 3],
                [0, -1, -2, -3],
                [0, 0.2, 0.4, 0.6]]

        result = utils.normalize_cost_matrix(test_matrix)

        round_values = lambda x: [round(v, 4) for v in x]
        expected_result = map(round_values, expected_result)
        result = map(round_values, result)

        self.assertEqual(expected_result, result)
