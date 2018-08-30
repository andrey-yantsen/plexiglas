FROM ubuntu:16.04

ENV CROSSCOMPILE_ARCH=arm-linux-gnueabihf
ENV ROOT_FILESYSTEM="/usr/$CROSSCOMPILE_ARCH"
ENV BUILD_HOST="x86_64"
ENV WORKING_DIRECTORY="/buildroot/python_xcompile"
ENV INSTALL_DIRECTORY="/buildroot/python_xcompile/_install"
ARG PYTHON_VERSION="2.7.12"
ENV SOURCE_DIRECTORY="Python-$PYTHON_VERSION"
ENV PYTHON_ARCHIVE="Python-$PYTHON_VERSION.tar.xz"
ENV ENABLE_MODULES="array cmath binascii _collections cPickle cStringIO datetime _elementtree fcntl _functools \
                    itertools _io math _md5 operator _random select _sha _socket _struct termios time unicodedata zlib \
                    xml sqlite ssl"
ENV RFS="$ROOT_FILESYSTEM"

RUN apt-get update && \
    apt-get install -y wget python make xz-utils gcc g++ gcc-$CROSSCOMPILE_ARCH zlib1g-dev libdb5.3 libdb5.3-dev \
    libreadline6-dev libc6-dev-i386 binutils-$CROSSCOMPILE_ARCH patch gcc-5-$CROSSCOMPILE_ARCH zip libffi-dev python-cffi python-cffi-backend

RUN mkdir -p $WORKING_DIRECTORY $INSTALL_DIRECTORY

WORKDIR $WORKING_DIRECTORY

RUN cd $WORKING_DIRECTORY && \
    wget --progress=dot:mega http://www.sqlite.org/2017/sqlite-autoconf-3160200.tar.gz && \
    tar xzf sqlite-autoconf-3160200.tar.gz && \
    cd sqlite-autoconf-3160200/ && \
    ./configure --host=$CROSSCOMPILE_ARCH --prefix=$INSTALL_DIRECTORY CC=$CROSSCOMPILE_ARCH-gcc && \
    make && \
    make install

RUN cd $WORKING_DIRECTORY && \
    wget --progress=dot:mega https://zlib.net/fossils/zlib-1.1.4.tar.gz && \
    tar xf zlib-1.1.4.tar.gz && \
    cd zlib-1.1.4 && \
    CC=$CROSSCOMPILE_ARCH-gcc LDSHARED="$CROSSCOMPILE_ARCH-gcc -shared -Wl,-soname,libz.so.1" ./configure --shared \
        --prefix=$INSTALL_DIRECTORY && \
    make && \
    make install

RUN cd $WORKING_DIRECTORY && \
    wget --progress=dot:mega https://www.openssl.org/source/openssl-1.0.1g.tar.gz && \
    tar -pxzf openssl-1.0.1g.tar.gz && \
    cd openssl-1.0.1g/ && \
    wget http://www.linuxfromscratch.org/patches/downloads/openssl/openssl-1.0.1g-fix_parallel_build-1.patch && \
    wget http://www.linuxfromscratch.org/patches/downloads/openssl/openssl-1.0.1g-fix_pod_syntax-1.patch && \
    patch -Np1 -i openssl-1.0.1g-fix_parallel_build-1.patch && \
    patch -Np1 -i openssl-1.0.1g-fix_pod_syntax-1.patch && \
    ./Configure linux-x86_64 os/compiler:$CROSSCOMPILE_ARCH-gcc --prefix=$INSTALL_DIRECTORY -fPIC && \
    make && \
    make install

RUN cd $WORKING_DIRECTORY/openssl-1.0.1g && \
    make clean && ./Configure linux-x86_64 --prefix=/usr -fPIC && \
    make && \
    make install

RUN cd $WORKING_DIRECTORY && \
    wget --progress=dot:mega http://www.python.org/ftp/python/$PYTHON_VERSION/$PYTHON_ARCHIVE && \
    rm -rf $SOURCE_DIRECTORY && \
    tar -xf $PYTHON_ARCHIVE

RUN cd $WORKING_DIRECTORY/$SOURCE_DIRECTORY && for module in $ENABLE_MODULES; do sed "s/^#$module/$module/" -i Modules/Setup.dist; done

ENV LDFLAGS="-L$INSTALL_DIRECTORY/lib"
ENV LD_LIBRARY_PATH="$INSTALL_DIRECTORY/lib:$ROOT_FILESYSTEM/lib/"
ENV CPPFLAGS="-I$ROOT_FILESYSTEM/include -I$INSTALL_DIRECTORY/include/python2.7  -I$INSTALL_DIRECTORY/include/openssl \
              -I$INSTALL_DIRECTORY/include \
              -I$WORKING_DIRECTORY/$SOURCE_DIRECTORY/Modules/_ctypes/libffi/arm-unknown-linux-gnueabihf/include"

RUN cd $WORKING_DIRECTORY/$SOURCE_DIRECTORY && make distclean || true && \
    ./configure --host=$CROSSCOMPILE_ARCH --build=$BUILD_HOST --prefix=$INSTALL_DIRECTORY \
        --disable-ipv6 --enable-unicode=ucs4 \
        ac_cv_file__dev_ptmx=no ac_cv_file__dev_ptc=no \
        ac_cv_have_long_long_format=yes && \
    make && \
    make install

RUN cd $WORKING_DIRECTORY/$SOURCE_DIRECTORY && make distclean || true && \
    LDFLAGS="-L/usr/lib" LD_LIBRARY_PATH="/usr/lib:/lib" CPPFLAGS="-I/usr/include -I/usr/include/python2.7 -I/usr/include/openssl" \
        ./configure --prefix=/usr \
        --disable-ipv6 --enable-unicode=ucs4 \
        ac_cv_file__dev_ptmx=no ac_cv_file__dev_ptc=no \
        ac_cv_have_long_long_format=yes && \
    make && \
    make install

RUN wget https://bootstrap.pypa.io/ez_setup.py -O - | python2.7

RUN cd $WORKING_DIRECTORY/$SOURCE_DIRECTORY/Modules/_ctypes/libffi && \
    ./configure --host=$CROSSCOMPILE_ARCH --build=$BUILD_HOST --prefix=$INSTALL_DIRECTORY && \
    make && \
    make install

RUN cd $WORKING_DIRECTORY/$SOURCE_DIRECTORY/Modules/_ctypes/libffi && \
    make clean && \
    ./configure --prefix= && \
    make && \
    make install

RUN cd $WORKING_DIRECTORY && \
    wget --progress=dot:mega https://pypi.python.org/packages/source/c/cffi/cffi-1.11.5.tar.gz && \
    tar -xzf cffi-1.11.5.tar.gz && \
    cd cffi-1.11.5 && \
    set -x && CPPFLAGS="-I/usr/include -I/usr/include/python2.7 -I/usr/include/openssl" python setup.py install

RUN cd $WORKING_DIRECTORY && \
    wget --progress=dot:mega https://pypi.python.org/packages/source/p/pycryptodome/pycryptodome-3.6.6.tar.gz && \
    tar -xzf pycryptodome-3.6.6.tar.gz && \
    cd pycryptodome-3.6.6 && \
    ARCH=$CROSSCOMPILE_ARCH PYTHONUSERBASE=$INSTALL_DIRECTORY CC=$CROSSCOMPILE_ARCH-gcc LDSHARED=$CROSSCOMPILE_ARCH-gcc \
        LDFLAGS="-L$INSTALL_DIRECTORY/lib -shared" \
        python setup.py install --user

RUN set -x && cd $WORKING_DIRECTORY && \
    wget --progress=dot:mega https://pypi.python.org/packages/source/a/argon2_cffi/argon2_cffi-18.3.0.tar.gz && \
    tar -xzf argon2_cffi-18.3.0.tar.gz && \
    cd argon2_cffi-18.3.0 && \
    sed -i 's/optimized =.*/optimized = False/' setup.py && \
    ARCH=$CROSSCOMPILE_ARCH PYTHONUSERBASE=$INSTALL_DIRECTORY CC=$CROSSCOMPILE_ARCH-gcc LDSHARED=$CROSSCOMPILE_ARCH-gcc \
        LDFLAGS="-L$INSTALL_DIRECTORY/lib -shared" \
        python setup.py install --user

RUN cd $WORKING_DIRECTORY && \
    wget --progress=dot:mega https://pypi.python.org/packages/source/c/cryptography/cryptography-0.9.3.tar.gz && \
    tar -xzf cryptography-0.9.3.tar.gz && \
    cd cryptography-0.9.3 && \
    ARCH=$CROSSCOMPILE_ARCH PYTHONUSERBASE=$INSTALL_DIRECTORY CC=$CROSSCOMPILE_ARCH-gcc LDSHARED=$CROSSCOMPILE_ARCH-gcc \
        LDFLAGS="-L$INSTALL_DIRECTORY/lib -shared" \
        python setup.py install --user

RUN cd $WORKING_DIRECTORY/cffi-1.11.5 && \
    rm -rf build dist && \
    ARCH=$CROSSCOMPILE_ARCH PYTHONUSERBASE=$INSTALL_DIRECTORY CC=$CROSSCOMPILE_ARCH-gcc LDSHARED=$CROSSCOMPILE_ARCH-gcc \
        LDFLAGS="-L$INSTALL_DIRECTORY/lib -shared" \
        python setup.py install --user

RUN cd $WORKING_DIRECTORY && \
    rm -rf _install_minimal && \
    mkdir -p _install_minimal/bin && \
    mkdir -p _install_minimal/lib/python2.7 && \
    mkdir -p _install_minimal/include && \
    cp $INSTALL_DIRECTORY/bin/python2.7 _install_minimal/bin/python && \
    cd $INSTALL_DIRECTORY/lib/ && \
    rm -rf python2.7-minimal && \
    cp -r python2.7 python2.7-minimal && \
    cd python2.7-minimal && \
    rm -r site-packages config lib-dynload && \
    rm *.doc *.txt && \
    cd $WORKING_DIRECTORY && \
    cp -r _install/lib/python2.7-minimal/* _install_minimal/lib/python2.7 && \
    cp -r _install/lib/python2.7/config _install_minimal/lib/python2.7/ && \
    cp -r _install/lib/python2.7/config _install_minimal/lib/python2.7/ && \
    cp -r _install/lib/python2.7/lib-dynload _install_minimal/lib/python2.7/ && \
    cp -r _install/lib/python2.7/site-packages _install_minimal/lib/python2.7/ && \
    cp -r _install/include/python2.7 _install_minimal/include/python2.7 && \
    cd _install_minimal && \
    rm -f $WORKING_DIRECTORY/../python-minimal.zip && \
    zip -r $WORKING_DIRECTORY/../python-minimal.zip . && \
    cd $INSTALL_DIRECTORY && \
    rm -rf lib/python2.7-minimal && \
    rm -f $WORKING_DIRECTORY/../python.zip && \
    zip -r $WORKING_DIRECTORY/../python.zip .
