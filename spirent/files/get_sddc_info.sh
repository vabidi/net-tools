#!/bin/bash

# takes 1 argument - the name of the sddc
# gets the pem files and txt file
# creates commands for ssh into popvm, hosts, edge, and saves then to file "sddc_cmds"


wget http://pa-dbc1132.eng.vmware.com/ankitparmar/externalsetup/$1/$1.pem -O ./sddc.pem 
wget http://pa-dbc1132.eng.vmware.com/ankitparmar/externalsetup/$1/$1-esx.pem -O ./sddc-esx.pem 
wget http://pa-dbc1132.eng.vmware.com/ankitparmar/externalsetup/$1/$1.txt -O ./sddc.txt

chmod 600 sddc.pem sddc-esx.pem

SDDC=$1
TF="sddc.txt"
ALF="sddc_cmds"
POPHOST=`cat  $TF | grep "^Agent IP" | sed 's#.*https://##g' | sed 's#/.*##g'`
echo "pop host is $POPHOST"
POPUSER=`cat $TF | grep "Agent Username" | awk '{print $4}'`
echo "pop user is $POPUSER"
ESX_0=`cat $TF | grep "ESX Host-0" | awk '{print $6}'`
echo "ESX_0 IP is $ESX_0"

ESX_1=`cat $TF | grep "ESX Host-1" | awk '{print $6}'`
echo "ESX_1 IP is $ESX_1"

ESX_2=`cat $TF | grep "ESX Host-2" | awk '{print $6}'`
echo "ESX_2 IP is $ESX_2"

Edge_0=`cat $TF | grep "Edge IPs" | awk '{print $5}'`
Edge_1=`cat $TF | grep "Edge IPs" | awk '{print $7}'`
Edge_pwd=`cat $TF | grep "Edge Password" | awk '{print $5}'`
echo "Edge_0 IP is $Edge_0 Edge_1 IP is $Edge_1 Password is $Edge_pwd"

Mgr_1=`cat $TF | grep "NSX IP" | awk '{print $4}'`
Mgr_pwd=`cat $TF | grep "Manager Password" | awk '{print $5}'`
echo "Mgr_1 IP is $Mgr_1  Password is $Mgr_pwd"


SSHOPT="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o loglevel=quiet"

CWD=`pwd`
PEM="$CWD/sddc.pem"
ESX_PEM="$CWD/sddc-esx.pem"

PCMD="ssh -W %h:%p -i $PEM $SSHOPT $POPUSER@$POPHOST"

rm $ALF


echo "esx0==ssh $SSHOPT -i $ESX_PEM -oProxyCommand='$PCMD' root@$ESX_0" >> $ALF
echo "esx1==ssh $SSHOPT -i $ESX_PEM -oProxyCommand='$PCMD' root@$ESX_1" >> $ALF
echo "esx2==ssh $SSHOPT -i $ESX_PEM -oProxyCommand='$PCMD' root@$ESX_2" >> $ALF
echo "popvm==ssh $SSHOPT -i $PEM $POPUSER@$POPHOST" >> $ALF
echo "edge0==sshpass  -p $Edge_pwd ssh $SSHOPT -oProxyCommand='$PCMD' root@${Edge_0}" >> $ALF
echo "edge1==sshpass  -p $Edge_pwd ssh $SSHOPT -oProxyCommand='$PCMD' root@${Edge_1}" >> $ALF
echo "scpr0==scp -r $SSHOPT -i $ESX_PEM -oProxyCommand='$PCMD' root@$ESX_0:/vmkstatsdir" >> $ALF
echo "scpr1==scp -r $SSHOPT -i $ESX_PEM -oProxyCommand='$PCMD' root@$ESX_1:/vmkstatsdir" >> $ALF
echo "scpr2==scp -r $SSHOPT -i $ESX_PEM -oProxyCommand='$PCMD' root@$ESX_2:/vmkstatsdir" >> $ALF


