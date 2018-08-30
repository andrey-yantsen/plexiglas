#!/bin/sh -x

set -e

#ssh root@mypassport.local "mkdir -p /DataVolume/python/"
#scp $(dirname $0)/python-minimal.zip root@mypassport.local:/DataVolume/python/python.zip
#ssh root@mypassport.local "cd /DataVolume/python/ && unzip -o python.zip && rm python.zip"
#ssh root@mypassport.local "curl https://bootstrap.pypa.io/get-pip.py --insecure | PYTHONHOME=/DataVolume/python/ /DataVolume/python/bin/python"
ssh root@mypassport.local "LC_ALL=en_US.UTF-8 PYTHONHOME=/DataVolume/python/ /DataVolume/python/bin/pip install -U --process-dependency-links plexiglas"

scp $(dirname $0)/plexiglas.service root@mypassport.local:/etc/systemd/system/
ssh root@mypassport.local "systemctl enable plexiglas.service"

ssh -t root@mypassport.local "LC_ALL=en_US.UTF-8 PYTHONHOME=/DataVolume/python/ /DataVolume/python/bin/plexiglas -d /DataVolume/PlexSync -i -n 'MyPassport Wireless Pro' -q"

ssh root@mypassport.local "systemctl start plexiglas.service"
