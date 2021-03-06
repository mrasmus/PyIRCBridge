#Based on http://www.osix.net/modules/article/?id=780

import sys
from socket import socket
import string
import os
from Queue import Queue
from threading import Thread
from time import sleep
from json import loads, dumps
from re import search, split, sub

IDENT='CBA Testbot'
REALNAME='Cloudboat Armada'
OWNER='mrasmus' #The bot owner's nick
EOL='\r\n'
DEBUG=True

def sendtosocket(s,msg):
	print 'DEBUG:Sending message on socket ' + str(s.fileno()) + ':' + msg 
	s.send(msg+EOL)

class Server(Thread):
	def __init__(self,name,host,channels,nick='cbirc',port=6667,serverpass=None,nspass=None,**kwargs):
		self.servername = name
		self.host = host
		self.serverpass = serverpass
		self.nspass = nspass
		self.port = port
		self.nick = nick
		self.channels = channels
		self.s = socket()
		self.targets = []
		super(Server, self).__init__(**kwargs)

	def run(self):
		self.s.connect((self.host, self.port))
		if (self.serverpass is not None):
			sendtosocket(self.s, 'PASS '+self.serverpass)
		sendtosocket(self.s,'NICK '+self.nick)
		sendtosocket(self.s,'USER '+IDENT+' '+self.host+' bla :'+REALNAME)
		done = False
		while not done:
			lines = self.s.recv(4096)
			if lines == '':
				done = True
				print '****Socket on ' + self.host + ' closed.'
			else:
				for line in [x for x in split(EOL,lines) if x != '']:
					print '****RAW:'+line
					if line.find('NOTICE ' + self.nick + ' :This nickname is registered.')!=-1:
						print "Identify to nickserv...\n"
						sendtosocket(self.s,'PRIVMSG NickServ IDENTIFY '+self.nspass)
					if (line.find('You are now identified for') != -1) or (line.find('End of /MOTD command') != -1):
						print '**************JOINING CHANNELS ON ' + self.host
						for chan in self.channels:
							sendtosocket(self.s,'JOIN '+chan)
							print '****Joined channel '+chan+' on '+self.host
					elif (line.split()[0]=='PING'):
						sendtosocket(self.s,'PONG '+line.rstrip().split()[1])
						print '****Sending:'+'PONG '+line.rstrip().split()[1][1:]
					else:
						for l in [l for l in split(EOL,line) if 'PRIVMSG #' in l]:
							m = search(':(.*?)!.* PRIVMSG (#[^ ,]+) :(.+)',l)
							if (m.group(3)[:7] == "\x01ACTION"):
								msg = '{'+m.group(1)+'} '+m.group(3)[8:]
							else:
								msg = '{'+m.group(1)+'}: '+m.group(3)
							print "Message on " + self.servername + m.group(2) + ": " + msg
							for t in self.targets:
								t.put(msg)

class Repeater(Thread):
	def __init__(self,sock,chan,**kwargs):
		self.q = Queue()
		self.s = sock
		self.channel = chan
		super(Repeater, self).__init__(**kwargs)

	def run(self):
		while True:
			sendtosocket(self.s,'PRIVMSG '+self.channel+' :'+self.q.get()+EOL)
			print 'Message sent to '+self.channel

servers = {} 
srvdict = loads(os.environ["IRCSERVERS"])
for key in srvdict.keys():
	srv=srvdict[key]
	servers[key] = Server(key,srv['host'],srv['channels'],srv['nick'],srv['port'],srv['serverpass'],srv['nspass'])
for server in servers.values():
	server.start()

sleep(5)

for sub in loads(os.environ['IRCSUBS']):
	print 'sending messages from ' + servers[sub[1]].servername + ' to '+servers[sub[0]].servername + sub[2]
	r = Repeater(servers[sub[0]].s,sub[2])
	r.start()
	servers[sub[1]].targets+=[r.q]

while True:
	#print '++++Received line: ||' + q1.get()
	pass
