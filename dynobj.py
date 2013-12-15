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


import paramiko
import re
import socket
import struct
import sys

DYNOBJ_COMMAND = 'dynamic_objects'
DEBUG = False

ERROR_TOKEN = '__ERROR__'

def debug(o, newLine=True):
	if DEBUG:
		sys.stderr.write(str(o))
		if newLine:
			sys.stderr.write('\n')

def aton(ipstr):
	return struct.unpack('!L', socket.inet_aton(ipstr))[0]

def ntoa(ip):
	return socket.inet_ntoa(struct.pack('!L', ip))

def validateToken(token):
	if not re.match(r'[a-zA-Z0-9_.-]+$', token):
		raise Exception('Invalid token:\n' + repr(token))

class Session(object):
	"""Implements an SSH session with a gateway."""

	def __init__(self, server, user='admin', password=None):
		"""Initializes the session object with a server address and credentials"""
		self.client = paramiko.SSHClient()
		self.client.load_system_host_keys()
		self.client.connect(server, username=user, password=password)

	def close(self):
		self.client.close()

	def run(self, *params):
		debug(params)
		cmd = [DYNOBJ_COMMAND]
		for p in params:
			cmd.append(p)
			if p == '&&':
				cmd.append(DYNOBJ_COMMAND)
			else:
				validateToken(p)
		cmd.extend(['||', 'echo', ERROR_TOKEN])

		debug(' '.join(cmd))
		stdin, stdout, stderr = self.client.exec_command(' '.join(cmd))
		out = [line.strip() for line in stdout.readlines()]
		debug(out)
		if 'File is empty' in out and params[0] == '-l':
			return []
		if ERROR_TOKEN in out:
			raise Exception('Error while running command:\n' + repr(out) +
					'\n' + repr(stderr.readlines()))
		return out

	def getObjects(self):
		"""Return a list of dynamic objects retrieved from the gateway"""
		lines = self.run('-l')

		objs = {}
		name = ''
		ranges = []

		for line in lines:
			if line.startswith('object name :'):
				name = line[len('object name :'):].strip()
			if line.startswith('range '):
				range = line.partition(':')[2].strip()
				begin = range.partition('\t')[0].strip()
				end = range.partition('\t')[2].strip()
				ranges.append((begin, end))
			if line == '':
				if name:
					objs[name] = ranges
					ranges = []
					name = ''
		return objs

	def getObject(self, name, doRaise=True):
		"""Return the address ranges currently associated with the dynamic object."""
		objs = self.getObjects()
		if name not in objs:
			if doRaise:
				raise Exception('Object does not exist: ' + repr(name))
			return None
		return objs[name]

	def printObject(self, name=None):
		"""Prints the addresses of a dynamic object with name name or all objects if no name is given."""
		if name is None:
			print self.getObjects()
			return
		print name + ':', self.getObject(name)

	def addObject(self, name, allowExisting=False):
		"""Creates a new empty dynamic object."""
		obj = self.getObject(name, False)
		if obj is None:
			self.run('-n', name)
			return
		if not allowExisting:
			raise Exception('Object already exists: ' + repr(name))

	def delObject(self, name):
		"""Deletes the dynamic object with name 'name'."""
		self.getObject(name) # assert that the object exists
		self.run('-do', name)

	def clearObject(self, name):
		"""Removes all address ranges from the given dynamic object."""
		obj = self.getObject(name)
		if not len(obj):
			# Object is already empty
			return
		params = ['-o', name, '-r'] + sum([list(r) for r in obj], []) + ['-d']
		self.run(*params)

	def delAddress(self, name, ipstr):
		"""Removes the specified address from the given dynamic object."""
		obj = self.getObject(name)

		ip = aton(ipstr)
		ranges = []
		to_add = ''

		for r in obj:
			begin = aton(r[0])
			end = aton(r[1])
			if not (begin <= ip <= end):
				continue
			if begin < ip:
				ranges.append(ntoa(begin))
				ranges.append(ntoa(ip - 1))
			if ip < end:
				ranges.append(ntoa(ip + 1))
				ranges.append(ntoa(end))
			break
		else:
			# No matching range was found
			raise Exception('No such address in object: %s in %s' %
					(repr(ipstr), repr(obj)))

		params = ['-o', name, '-r', r[0], r[1], '-d']
		if len(ranges):
			params.extend(['&&', '-o', name, '-r'] + ranges + ['-a'])
		self.run(*params)

	def addAddress(self, name, ip):
		"""Adds the specified address from the given dynamic object."""
		self.getObject(name) # assert that the object exists
		self.run('-o', name, '-r', ip, ip, '-a')

	def setAddresses(self, name, ips):
		"""Set a dynamic object to resolve to the given list of IP addresses."""
		obj = self.getObject(name, False)
		if obj is None:
			self.addObject(name)
			obj = []
		addrsOld = []
		addrsNew = []
		for r in obj:
			addrsOld.extend(range(aton(r[0]), aton(r[1])))
			addrsOld.append(aton(r[1]))
		for ip in ips:
			addrsNew.append(aton(ip))
		toRemove = set(addrsOld) - set(addrsNew)
		toAdd = set(addrsNew) - set(addrsOld)
		for addr in toAdd:
			self.addAddress(name, ntoa(addr))
		for addr in toRemove:
			self.delAddress(name, ntoa(addr))

if __name__ == '__main__':
	s = None
	try:
		s = Session('192.168.133.99') # Session(GATEWAY, ADMIN, ADMIN_PASSWORD)
		s.printObject()
		s.addObject('obj1', True)
		s.printObject('obj1')
		s.addAddress('obj1', '10.2.3.4')
		s.printObject('obj1')
		s.addAddress('obj1', '10.2.3.5')
		s.printObject('obj1')
		s.addAddress('obj1', '10.2.3.7')
		s.printObject('obj1')
		s.addAddress('obj1', '10.2.3.6')
		s.printObject('obj1')
		s.delAddress('obj1', '10.2.3.5')
		s.printObject('obj1')
		s.delAddress('obj1', '10.2.3.7')
		s.printObject('obj1')
		s.delAddress('obj1', '10.2.3.6')
		s.printObject('obj1')
		s.clearObject('obj1')
		s.printObject('obj1')
		s.delObject('obj1')
		s.printObject()
	finally:
		if s is not None:
			s.close()

