# Overview
This page documents Python tools and scripts that could be used to update dynamic objects over SSH

# Use Cases
Dynamic objects are powerful tools for dynamically modifying the behavior of the security policy without requiring a full policy installation.

Possible source of information include:

+ Orchestration systems
+ DNS

# dynobj.py
implements a Python module that could be used to manipulate dynamic objects on the gateway over SSH

For the latest documentation - run:
	python -c 'import dynobj; help(dynobj)'

# dns2dyn.py
	Usage: dns2dyn.py options
	Options:
	  -h, --help            show this help message and exit
	  -f FILE, --file=FILE  read configuration from FILE
	  -g GATEWAY, --gateway=GATEWAY
	                        connect to GATEWAY
	  -u USER, --user=USER  the admin username
	  -p PASSWORD, --password=PASSWORD
	                        the admin password. use '-' to read from the console

This tool takes a configuration file in JSON format. 
For example: dns2dyn.json

	{
		"dyn1": ["www.google.com", "cnn.com" ],
		"dyn2": ["mail.google.com", "mail.yahoo.com"]
	}

In the example above:
The dynamic object named 'dyn1' would be resolved to the list of addresses associated in DNS with www.google.com, and cnn.com
The dynamic object named 'dyn2' would be resolved to the list of addresses associated in DNS with mail.google.com, and mail.yahoo.com

# Notes:
+ Using a cron job, the script could run periodically
+ If a host name resolves to multiple IP addresses, the script would add all of them to the dynamic object
+ The set of resolved IP addresses depends on where the script is run. (e.g. running the script in different geographic locations could yield different addresses)
+ In addition to password based authentication, the script supports SSH client authentication with public keys
+ The code depends on the popular Python SSH module [paramiko](https://github.com/paramiko/paramiko)
+ Today, dynamic objects in Check Point disable templates generation for all rules that follow a rule with a dynamic object


