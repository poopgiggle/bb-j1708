bb-j1708
========

Python J1708 implementation for BeagleBone

OK, getting this thing to work might be tricky.

1. Needs to be used from Python3 because it relies on some Python3 features.

2. Relies on Adafruit's BBIO python package here: https://learn.adafruit.com/setting-up-io-python-library-on-beaglebone-black/overview

Follow the instructions to clone their github repo and build from scratch.

Except that package won't build for Python3 by default, so we have to fix their stuff. Do this as follows:

1. Run '2to3 -w setup.py' to get it to run with python3.
2. open source/common.c and fix all calls to fprintf. Example: fprintf(file, name) should be fprintf(file, "%s", name). If you don't do this,
   gcc compiles with -Wformat-security by default and it will throw an error.
3. In setup.py, comment out the line that begins with Extension('Adafruit_BBIO.SPI'
   There's an error in the SPI module that I don't feel like tracking down.

NOW you can install it with the command "sudo python3 setup.py install"