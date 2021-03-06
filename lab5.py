#!/usr/bin/python

"""
Start up a Simple topology for CS144
"""

from mininet.net import Mininet
from mininet.node import Controller, RemoteController
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.topo import Topo
from mininet.util import quietRun
from mininet.moduledeps import pathCheck

from sys import exit
import os.path
from subprocess import Popen, STDOUT, PIPE

IPBASE = '10.3.0.0/16'
ROOTIP = '10.3.0.100/16'
IPCONFIG_FILE = './IP_CONFIG'
IP_SETTING={}

class CS144Topo( Topo ):
    "CS 144 Lab 5 Topology"
    
    def __init__( self, *args, **kwargs ):
        Topo.__init__( self, *args, **kwargs )
        server1 = self.add_host( 'server1' )
        server2 = self.add_host( 'server2' )
        nat = self.add_switch( 'sw0' )
        bridge = self.add_switch( 'sw1' )
        root = self.add_host( 'root', inNamespace=False )
        self.add_link(root, nat)
        for h in server1, server2, nat: #client, root:
            self.add_link( h,  bridge)


class CS144Controller( Controller ):
    "Controller for CS144 Multiple IP Bridge"

    def __init__( self, name, inNamespace=False, command='controller',
                 cargs='-v ptcp:%d', cdir=None, ip="127.0.0.1",
                 port=6633, **params ):
        """command: controller command name
           cargs: controller command arguments
           cdir: director to cd to before running controller
           ip: IP address for controller
           port: port for controller to listen at
           params: other params passed to Node.__init__()"""
        Controller.__init__( self, name, ip=ip, port=port, **params)

    def start( self ):
        """Start <controller> <args> on controller.
            Log to /tmp/cN.log"""
        pathCheck( self.command )
        cout = '/tmp/' + self.name + '.log'
        if self.cdir is not None:
            self.cmd( 'cd ' + self.cdir )
        self.cmd( self.command, self.cargs % self.port, '>&', cout, '&' )

    def stop( self ):
        "Stop controller."
        self.cmd( 'kill %' + self.command )
        self.terminate()


def startsshd( host ):
    "Start sshd on host"
    stopsshd()
    info( '*** Starting sshd\n' )
    name, intf, ip = host.name, host.defaultIntf(), host.IP()
    banner = '/tmp/%s.banner' % name
    host.cmd( 'echo "Welcome to %s at %s" >  %s' % ( name, ip, banner ) )
    host.cmd( '/usr/sbin/sshd -o "Banner %s"' % banner, '-o "UseDNS no"' )
    info( '***', host.name, 'is running sshd on', intf, 'at', ip, '\n' )


def stopsshd():
    "Stop *all* sshd processes with a custom banner"
    info( '*** Shutting down stale sshd/Banner processes ',
          quietRun( "pkill -9 -f Banner" ), '\n' )


def starthttp( host ):
    "Start simple Python web server on hosts"
    info( '*** Starting SimpleHTTPServer on host', host, '\n' )
    #host.cmd( 'cd ~/http_%s/; python -m SimpleHTTPServer 80 >& /tmp/%s.log &' % (host.name, host.name) )
    #host.cmd( 'cd ~/http_%s/; nohup python2.7 ~/http_%s/webserver.py >& /tmp/%s.log &' % (host.name, host.name, host.name) )
    host.cmd( 'cd ~/http_%s/; nohup python2.7 ~/http_%s/webserver.py &' % (host.name, host.name) )
    #host.cmd( 'cd ~/http_%s/; screen -S webserver -D -R python2.7 ~/http_%s/webserver.py ' % (host.name, host.name) )


def stophttp():
    "Stop simple Python web servers"
    info( '*** Shutting down stale SimpleHTTPServers', 
          quietRun( "pkill -9 -f SimpleHTTPServer" ), '\n' )    
    info( '*** Shutting down stale webservers', 
          quietRun( "pkill -9 -f webserver.py" ), '\n' )    
    
def set_default_route(host):
    info('*** setting default gateway of host %s\n' % host.name)
    if(host.name == 'server1'):
        routerip = IP_SETTING['sw0-eth2']
    elif(host.name == 'server2'):
        routerip = IP_SETTING['sw0-eth2']
    print host.name, routerip
    host.cmd('route add %s/32 dev %s-eth0' % (routerip, host.name))
    host.cmd('route add default gw %s dev %s-eth0' % (routerip, host.name))
    #HARDCODED
    #host.cmd('route del -net 10.3.0.0/16 dev %s-eth0' % host.name)
    ips = IP_SETTING[host.name].split(".") 
    host.cmd('route del -net %s.0.0.0/8 dev %s-eth0' % (ips[0], host.name))

def get_ip_setting():
    if (not os.path.isfile(IPCONFIG_FILE)):
        return -1
    f = open(IPCONFIG_FILE, 'r')
    for line in f:
        name, ip = line.split()
        print name, ip
        IP_SETTING[name] = ip
    return 0

def cs144net():
    stophttp()
    "Create a simple network for cs144"
    r = get_ip_setting()
    if r == -1:
        exit("Couldn't load config file for ip addresses, check whether %s exists" % IPCONFIG_FILE)
    else:
        info( '*** Successfully loaded ip settings for hosts\n %s\n' % IP_SETTING)

    topo = CS144Topo()
    info( '*** Creating network\n' )
    net = Mininet( topo=topo, controller=RemoteController, ipBase=IPBASE )
    net.start()
    server1, server2, nat = net.get( 'server1', 'server2', 'sw0')
    s1intf = server1.defaultIntf()
    s1intf.setIP('%s/8' % IP_SETTING['server1'])
    s2intf = server2.defaultIntf()
    s2intf.setIP('%s/8' % IP_SETTING['server2'])

    cmd = ['ifconfig', "eth1"]
    process = Popen(cmd, stdout=PIPE, stderr=STDOUT)
    hwaddr = Popen(["grep", "HWaddr"], stdin=process.stdout, stdout=PIPE)
    eth1_hw = hwaddr.communicate()[0]
    info( '*** setting mac address of sw0-eth1 (nat) the same as eth1 (%s)\n' % eth1_hw.split()[4])
    nat.intf('sw0-eth1').setMAC(eth1_hw.split()[4])
    
   
    #for host in server1, server2, client:
    for host in server1, server2:
        set_default_route(host)
    starthttp( server1 )
    starthttp( server2 )
    CLI( net )
    stophttp()
#    stopsshd()
    net.stop()


if __name__ == '__main__':
    setLogLevel( 'info' )
    cs144net()
