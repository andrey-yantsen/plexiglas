#!/bin/bash

set -e

# Validate tag

if [ -z "${TRAVIS_TAG}" ]
then
    echo "No TRAVIS_TAG in ENV"
    exit 1
fi

if ! [[ "${TRAVIS_TAG}" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]
then
    echo "Tag should be formatted as v0.1.2"
    exit 1
fi

package_version=$(echo "${TRAVIS_TAG}" | sed 's/v//')

sed -i "s/_CI_SET_VERSION_/${package_version}/g" plexiglas/*.py
