from setuptools import setup
import re
from io import open

# Get the current version
version = None
with open('plexiglas/__init__.py') as handle:
    for line in handle.readlines():
        if line.startswith('__version__'):
            version = re.findall("'([0-9\.]+?)'", line)[0]
            break

if version is None:
    print('Unable to find package version')
    exit(1)

# Get README.md contents
# read the contents of your README file
from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    readme = f.read()

# Get requirments
requirements = []
dependency_links = []
with open('requirements.txt') as handle:
    for line in handle.readlines():
        if not line.startswith('#'):
            if '://' in line:
                link = line.strip()
                dependency_links.append(link)
                requirements.append(re.findall("#egg=(.*?)-[\d.]+", line)[0])
            else:
                package = line.strip().split('=', 1)[0]
                requirements.append(package)

setup(
    name='plexiglas',
    version=version,
    packages=['plexiglas'],
    package_dir={'plexiglas': 'plexiglas'},
    url='https://github.com/andrey-yantsen/plexiglass',
    license='MIT',
    author='Andrey Yantsen',
    author_email='andrey@janzen.su',
    description='Tool for downloading videos from your Plex server to an external HDD',
    include_package_data=True,
    long_description=readme,
    long_description_content_type='text/markdown',
    install_requires=requirements,
    dependency_links=dependency_links,
    entry_points={'console_scripts': ['plexiglas = plexiglas.cli:main']},
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
    ],
)
