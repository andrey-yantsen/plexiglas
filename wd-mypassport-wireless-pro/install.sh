#!/bin/sh -x

set -e

ssh root@mypassport.local "mkdir -p /DataVolume/python/"
scp $(dirname $0)/plexiglas.service root@mypassport.local:/etc/systemd/system/
scp $(dirname $0)/python-minimal.zip root@mypassport.local:/DataVolume/python/python.zip

ssh root@mypassport.local << END
cd /DataVolume/python/ && unzip -o python.zip && rm python.zip
curl https://bootstrap.pypa.io/get-pip.py --insecure | PYTHONHOME=/DataVolume/python/ /DataVolume/python/bin/python
LC_ALL=en_US.UTF-8 PYTHONHOME=/DataVolume/python/ /DataVolume/python/bin/pip install -U --process-dependency-links plexiglas
END

ssh -t root@mypassport.local "LC_ALL=en_US.UTF-8 PYTHONHOME=/DataVolume/python/ /DataVolume/python/bin/plexiglas -d /DataVolume/PlexSync -i -n 'MyPassport Wireless Pro' -q"

ssh root@mypassport.local << END
systemctl enable plexiglas.service
systemctl start plexiglas.service
END
