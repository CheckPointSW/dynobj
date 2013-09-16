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
   
import json
import getpass
import socket
import argparse

from dynobj import Session

#{
#	"dynObj1" : ["host1.example.com", "host2.example.com" ],
#	"dynObj2" : ["host1.example2.com", "host2.example2.com" ]
#}

obj2addresses = {}
dnsCache = {}

def readConf(filename):
	with open(filename) as f:
		obj = json.load(f)

	for name, value in obj.items():
		del obj[name]
		obj[str(name)] = value
		
	return obj

def resolveHost(hostname):
	if not hostname in dnsCache:
		dnsCache[hostname] = socket.gethostbyname_ex(str(hostname))[2]
	return dnsCache[hostname]
	
def resolveDynObj(name, hosts):
	obj2addresses[name] = []
	for hostname in hosts:
		obj2addresses[name].extend(resolveHost(hostname))
	obj2addresses[name] = list(set(obj2addresses[name]))

def updateDynObj(session, name, addresses):
	session.setAddresses(name, addresses)

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("-f", "--file", dest="filename", required=True,
	                  help="read configuration from FILE", metavar="FILE")
	parser.add_argument("-g", "--gateway", dest="gateway",  required=True,
					  help="connect to GATEWAY")
	parser.add_argument("-u", "--user", dest="user", default="admin",
					  help="the admin username")
	parser.add_argument("-p", "--password", dest="password", default=None,
					  help="the admin password. Use '-' to read from the console")

	args = parser.parse_args()

	if args.password == '-':
		args.password = getpass.getpass()

	conf = readConf(args.filename)
	session = None
	try:
		for name, hosts in conf.items():
			resolveDynObj(name, hosts)
		session = Session(args.gateway, args.user, args.password)
		for name, addresses in obj2addresses.items():
			updateDynObj(session, name, addresses)
	finally:
		if session is not None:
			session.close()


if __name__ == '__main__':
	main()
		
