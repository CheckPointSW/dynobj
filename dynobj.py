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

"""Remotely manage dynamic objects"""


import logging
import os
import re
import socket
import struct
import subprocess
import sys
import tempfile


_DYNOBJ_COMMAND = 'dynamic_objects'
_ERROR_TOKEN = '__ERROR__'


# Initialize logging
logging.basicConfig()
debug = logging.getLogger(__name__).debug
# uncomment for debug logs
# logging.getLogger(__name__).setLevel(logging.DEBUG)


def _aton(ipstr):
    return struct.unpack('!L', socket.inet_aton(ipstr))[0]


def _ntoa(ipaddr):
    return socket.inet_ntoa(struct.pack('!L', ipaddr))


def _validate_token(token):
    if not re.match(r'[a-zA-Z0-9_.-]+$', token):
        raise Exception('Invalid token:\n' + repr(token))


def _get_lines(file_obj):
    """Return all the lines in file_obj."""
    return [line.strip() for line in file_obj.readlines()]


def _ssh_exec(conf):
    """Implement remote exec client over ssh"""
    from paramiko import SSHClient

    def _rexec(cmd):
        client = SSHClient()
        client.load_system_host_keys()
        try:
            client.connect(
                conf['gateway'],
                username=conf.get('user', 'admin'),
                password=conf.get('password', None),
                key_filename=conf.get('key', None))
            dummy, stdout, stderr = client.exec_command(' '.join(cmd))
            return _get_lines(stdout), _get_lines(stderr)
        finally:
            client.close()
    return _rexec


def _cprid_exec(conf):
    """Implement remote exec client using cprid_util."""
    gateway = conf['gateway']
    tmpdir = os.environ.get('CPDIR')
    if tmpdir is not None:
        tmpdir = os.path.join(tmpdir, 'tmp')
    if tmpdir is None or not os.path.exists(tmpdir):
        raise Exception('Cannot find $CPDIR/tmp')

    def _mktemp(tag):
        return tempfile.NamedTemporaryFile(prefix='cprid_' + tag + '_',
                                           dir=tmpdir)

    def _rexec(cmd):
        with _mktemp('out') as out, _mktemp('err') as err:
            subprocess.call([
                'cprid_util', '-server', gateway, 'rexec',
                '-stdout', out.name, '-stderr', err.name,
                '-rcmd', 'bash', '-c', ' '.join(cmd)])
            out_lines = _get_lines(out)
            err_lines = _get_lines(err)
            return out_lines, err_lines
    return _rexec


def _local_exec(dummy):
    """Implement a local "remote" exec client"""
    def _rexec(cmd):
        out, err = subprocess.Popen(
            ['bash', '-c', ' '.join(cmd)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE).communicate()
        return out.split('\n'), err.split('\n')
    return _rexec


class Manager(object):
    """An API to manage dynamic objects remotely"""
    def __init__(self, scheme, conf):
        exec_func = {
            'ssh': _ssh_exec,
            'cprid': _cprid_exec,
            'local': _local_exec,
        }
        if scheme not in exec_func:
            raise Exception('Unsupported scheme "{0}"'.format(scheme))

        self.rexec = exec_func[scheme](conf)

    def _run(self, *params):
        """Run a remote command to manipulate dynamic objects."""
        debug(params)
        cmd = [_DYNOBJ_COMMAND]
        for param in params:
            cmd.append(param)
            if param == '&&':
                cmd.append(_DYNOBJ_COMMAND)
            else:
                _validate_token(param)
        cmd.extend(['||', 'echo', _ERROR_TOKEN])

        debug(' '.join(cmd))
        out, err = self.rexec(cmd)
        debug(out)
        debug('')
        if 'File is empty' in out and params[0] == '-l':
            return []
        if _ERROR_TOKEN in out:
            raise Exception('Error while running command:\n' + repr(out) +
                            '\n' + repr(err))
        return out

    def get_objects(self):
        """Return a list of dynamic objects retrieved from the gateway."""
        lines = self._run('-l')

        objs = {}
        name = ''
        ranges = []

        for line in lines:
            if line.startswith('object name :'):
                name = line[len('object name :'):].strip()
            if line.startswith('range '):
                range_str = line.partition(':')[2].strip()
                begin = range_str.partition('\t')[0].strip()
                end = range_str.partition('\t')[2].strip()
                ranges.append((begin, end))
            if line == '':
                if name:
                    objs[name] = ranges
                    ranges = []
                    name = ''
        return objs

    def get_object(self, name, do_raise=True):
        """Return the address ranges of the dynamic object 'name'."""
        objs = self.get_objects()
        if name not in objs:
            if do_raise:
                raise Exception('Object does not exist: ' + repr(name))
            return None
        return objs[name]

    def print_object(self, name=None):
        """Print the addresses of a dynamic object

        use the object with the name 'name' or all objects if no name is given.

        """
        if name is None:
            print self.get_objects()
            return
        print name + ':', self.get_object(name)

    def add_object(self, name, allow_existing=False):
        """Create a new empty dynamic object named 'name'."""
        obj = self.get_object(name, False)
        if obj is None:
            self._run('-n', name)
            return
        if not allow_existing:
            raise Exception('Object already exists: ' + repr(name))

    def del_object(self, name):
        """Delete the dynamic object 'name'."""
        self.get_object(name)  # assert that the object exists
        self._run('-do', name)

    def clear_object(self, name):
        """Remove all address ranges from the dynamic object 'name'."""
        obj = self.get_object(name)
        if not len(obj):
            # Object is already empty
            return
        params = ['-o', name, '-r'] + sum([list(r) for r in obj], []) + ['-d']
        self._run(*params)

    def del_address(self, name, ipstr):
        """Remove the specified address from the dynamic object 'name'."""
        obj = self.get_object(name)

        ipaddr = _aton(ipstr)
        ranges = []

        for iprange in obj:
            begin = _aton(iprange[0])
            end = _aton(iprange[1])
            if not (begin <= ipaddr <= end):
                continue
            if begin < ipaddr:
                ranges.append(_ntoa(begin))
                ranges.append(_ntoa(ipaddr - 1))
            if ipaddr < end:
                ranges.append(_ntoa(ipaddr + 1))
                ranges.append(_ntoa(end))
            matching = iprange
            break
        else:
            # No matching range was found
            raise Exception('No such address in object: %s in %s' %
                            (repr(ipstr), repr(obj)))

        params = ['-o', name, '-r', matching[0], matching[1], '-d']
        if len(ranges):
            params.extend(['&&', '-o', name, '-r'] + ranges + ['-a'])
        self._run(*params)

    def add_address(self, name, ipstr):
        """Add the specified address to the dynamic object 'name'."""
        self.get_object(name)  # assert that the object exists
        self._run('-o', name, '-r', ipstr, ipstr, '-a')

    def set_addresses(self, name, ips):
        """Set a dynamic object 'name' to resolve to the address list 'ips'."""
        obj = self.get_object(name, False)
        if obj is None:
            self.add_object(name)
            obj = []
        addrs_old = []
        addrs_new = []
        for iprange in obj:
            addrs_old.extend(range(_aton(iprange[0]), _aton(iprange[1])))
            addrs_old.append(_aton(iprange[1]))
        for ipstr in ips:
            addrs_new.append(_aton(ipstr))
        to_remove = set(addrs_old) - set(addrs_new)
        to_add = set(addrs_new) - set(addrs_old)
        for addr in to_add:
            self.add_address(name, _ntoa(addr))
        for addr in to_remove:
            self.del_address(name, _ntoa(addr))


def _main(argv):
    if len(argv) < 2 or len(argv) % 2:
        raise Exception("""
        Usage:
            {0} ssh gateway SERVER [user USER [password PASSWORD]]
            {0} cprid gateway SERVER
            {0} local
        """.format(argv[0]))

    manager = Manager(argv[1], dict(zip(argv[2::2], argv[3::2])))
    myobj = 'obj1'
    manager.print_object()
    manager.add_object(myobj, True)
    manager.print_object(myobj)
    manager.add_address(myobj, '10.2.3.4')
    manager.print_object(myobj)
    manager.add_address(myobj, '10.2.3.5')
    manager.print_object(myobj)
    manager.add_address(myobj, '10.2.3.7')
    manager.print_object(myobj)
    manager.add_address(myobj, '10.2.3.6')
    manager.print_object(myobj)
    manager.del_address(myobj, '10.2.3.5')
    manager.print_object(myobj)
    manager.del_address(myobj, '10.2.3.7')
    manager.print_object(myobj)
    manager.del_address(myobj, '10.2.3.6')
    manager.print_object(myobj)
    manager.clear_object(myobj)
    manager.print_object(myobj)
    manager.del_object(myobj)
    manager.print_object()

if __name__ == '__main__':
    _main(sys.argv)
