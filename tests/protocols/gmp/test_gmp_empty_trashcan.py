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

import unittest

from gvm.xml import _GmpCommandFactory as GmpCommandFactory


class GMPEmptyTrashcanCommandTestCase(unittest.TestCase):
    def setUp(self):
        self.gmp = GmpCommandFactory()

    def tearDown(self):
        pass

    def test_empty_trashcan(self):
        cmd = self.gmp.empty_trashcan_command()

        self.assertEqual('<empty_trashcan/>', cmd)


if __name__ == '__main__':
    unittest.main()
