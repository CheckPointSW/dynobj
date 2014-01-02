# Overview
This page documents Python scripts that could be used to update dynamic objects over multiple remote access methods.


# Use Cases
Dynamic objects are powerful tools for dynamically modifying the behavior of the security policy without requiring a full policy installation.

Possible source of information include:

+ Orchestration systems
+ DNS


# dynobj.py
A Python module that implements an API for manipulating dynamic objects on a remote gateway. Remote access can be done over SSH, with CPRID, or by running local commands on the gateway itself..

For the latest documentation - run:
	python -c 'import dynobj; help(dynobj)'


# dns2dyn.py
A script to manage dynamic objects that map to the addresses of domain names.

	Usage: dns2dyn.py [-h] -f FILE -s {ssh,cprid,local} [-g GATEWAY] [-u USER]
	                  [-p PASSWORD] [-i KEY] [-d]

	optional arguments:
	  -h, --help            show this help message and exit
	  -f FILE, --file FILE  read configuration from FILE
	  -s {ssh,cprid,local}, --scheme {ssh,cprid,local}
	                        method of remote execution
	  -g GATEWAY, --gateway GATEWAY
	                        connect to GATEWAY
	  -u USER, --user USER  the admin username
	  -p PASSWORD, --password PASSWORD
	                        the admin password. Use '-' to read from the console
	  -i KEY, --identity KEY
	                        the admin private key file
	  -d, --debug           enable debug


The script uses a configuration file, for example: dns2dyn.json

	{
		"dyn1": ["www.google.com", "cnn.com" ],
		"dyn2": ["mail.google.com", "mail.yahoo.com"]
	}

In the example above:
The dynamic object named 'dyn1' would be resolved to the list of addresses associated in DNS with www.google.com, and cnn.com
The dynamic object named 'dyn2' would be resolved to the list of addresses associated in DNS with mail.google.com, and mail.yahoo.com

## Usage example:

	dns2dyn.py -f dns2dyn.json -s ssh -g GATEWAY -u admin

This will apply the configuration in the file dns2dyn.json to the gateway `GATEWAY` using remote access over SSH with the user `admin`. The session will use public key authentication, where the private key is retrieved from an SSH agent or by searching the default SSH directory (`~/.ssh`). If the `-p` option is used (use: `dns2dyn.py -h`, to see all the options), then a password can be specified for the user or the private key as needed. It is also possible to use `-i KEY-FILE` to point to a specific private key file.

# Notes:
+ Using a cron job, the script could run periodically
+ If a host name resolves to multiple IP addresses, the script would add all of them to the dynamic object
+ The set of resolved IP addresses depends on where the script is run. (e.g. running the script in different geographic locations could yield different addresses)
+ Access to the gateway is supported over SSH from any allowed client, from the management server using CPRID (option `-s cprid`), or locally on the gateway itself (option `-s local`) - this assumes that python is available on the gateway machine
+ For SSH access, the code depends on the popular Python SSH module [paramiko](https://github.com/paramiko/paramiko)
+ Currently, dynamic objects in Check Point disable template generation for all rules that follow a rule with a dynamic object


