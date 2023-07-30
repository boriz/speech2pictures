#/bin/bash

cd /usr/lib/wsl/lib/
rm -r libcuda.so.1
rm -r libcuda.so
ln -s libcuda.so.1.1 libcuda.so.1
ln -s libcuda.so.1.1 libcuda.so
ldconfig
