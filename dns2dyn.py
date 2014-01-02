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

"""A utility to manage dynamic objects that are mapped to domain names."""

import argparse
import json
import getpass
import socket

import dynobj

#{
#    "dynObj1" : ["host1.example.com", "host2.example.com" ],
#    "dynObj2" : ["host1.example2.com", "host2.example2.com" ]
#}


def read_conf(filename):
    """Read a JSON file with a mapping between dynobj name to domain names."""
    with open(filename) as file_obj:
        obj = json.load(file_obj)

    for name, value in obj.items():
        del obj[name]
        obj[str(name)] = value

    return obj


class Resolver:
    """Implement a simple domain name to address resolver.

    Use the an instance as a function to resolve host names.

    """
    def __init__(self):
        self._cache = {}

    def __call__(self, what):
        if hasattr(what, '__iter__'):
            result = []
            for host in what:
                result.extend(self(host))
            result = list(set(result))
        else:
            if not what in self._cache:
                self._cache[what] = socket.gethostbyname_ex(str(what))[2]
            result = self._cache[what]
        dynobj.debug('%s -> %s', what, result)
        return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', dest='filename', required=True,
        help='read configuration from FILE', metavar='FILE')
    parser.add_argument('-s', '--scheme', dest='scheme', required=True,
        choices=['ssh', 'cprid', 'local'],
        help='method of remote execution')
    parser.add_argument('-g', '--gateway', dest='gateway',
        help='connect to GATEWAY')
    parser.add_argument('-u', '--user', dest='user', default='admin',
        help='the admin username')
    parser.add_argument('-p', '--password', dest='password', default=None,
        help='the admin password. Use \'-\' to read from the console')
    parser.add_argument('-i', '--identity', dest='key', default=None,
        help='the admin private key file')
    parser.add_argument('-d', '--debug', dest='debug', action='store_true',
        default=False, help='enable debug')

    args = parser.parse_args()

    if args.debug:
        dynobj.logging.getLogger(dynobj.__name__).setLevel(dynobj.logging.DEBUG)

    if args.password == '-':
        args.password = getpass.getpass()

    conf = read_conf(args.filename)
    manager = dynobj.Manager(args.scheme, vars(args))
    resolve = Resolver()
    for name, hosts in conf.items():
        manager.set_addresses(name, resolve(hosts))


if __name__ == '__main__':
    main()

