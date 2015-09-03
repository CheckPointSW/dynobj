#!/usr/bin/env python

#   Copyright 2013 Check Point Software Technologies LTD
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""Tester"""

import sys

import dynobj


def _main(argv):
    if len(argv) < 2 or len(argv) % 2:
        raise Exception("""
        Usage:
            {0} ssh gateway SERVER [user USER [password PASSWORD]]
            {0} cprid gateway SERVER
            {0} local
        """.format(argv[0]))

    manager = dynobj.Manager(argv[1], dict(zip(argv[2::2], argv[3::2])))
    myobj = 'obj1'
    manager.print_object()
    manager.add_object(myobj, True)
    manager.print_object(myobj)
    manager.add_address(myobj, '10.2.3.4/31')
    manager.print_object(myobj)
    manager.add_address(myobj, '10.2.3.6/31')
    manager.print_object(myobj)
    manager.add_address(myobj, '10.2.3.13/31')
    manager.print_object(myobj)
    manager.add_address(myobj, '10.2.3.8')
    manager.print_object(myobj)
    manager.add_address(myobj, '10.2.3.9')
    manager.print_object(myobj)
    manager.del_address(myobj, '10.2.3.5-10.2.3.6')
    manager.print_object(myobj)
    manager.del_address(myobj, '10.2.3.7/30')
    manager.print_object(myobj)
    manager.set_addresses(myobj, ['10.2.3.2/30', '10.2.3.4',
                                  '10.2.3.8-10.2.3.11'])
    manager.print_object(myobj)
    manager.clear_object(myobj)
    manager.print_object(myobj)
    manager.del_object(myobj)
    manager.print_object()

if __name__ == '__main__':
    _main(sys.argv)
