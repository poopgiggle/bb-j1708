#!/usr/bin/python3



import serial
import time
from multiprocessing import Process, Pipe, Lock
from functools import reduce
import struct
import Adafruit_BBIO.GPIO as GPIO
#TODO: need a thread that monitors the J1708 bus and continually places messages in the receive buffer.
#      upon initialization, thread needs to spawn and synchronize itself with the J1708 bus.

TENBITTIMES = .0010417
GPIO.setup("GPIO1_28",GPIO.IN)

def toSignedChar(num):
	if type(num) is bytes:
		return struct.unpack('b',num)[0]
	else:
		return struct.unpack('b',struct.pack('B',num & 0xFF))[0]

def checksum(msg):
	return toSignedChar(~reduce(lambda x,y: (x + y) & 0xFF, list(msg)) + 1)

def check(msg):
	if type(msg[0]) is bytes:
		thismsg = list(map(lambda x: int.from_bytes(x,byteorder='big'), msg))
	else:
		thismsg = msg
	return toSignedChar(reduce(lambda x,y: (x+y) & 0xFF, list(thismsg)))

def initialize(busport,buslock):
	synced = False
	buslock.acquire()
	qtime = time.time()
	busport.flushInput()
	busport.timeout = 0
	while not synced:
		#print(time.clock())
#		a = busport.read(1)
		if not GPIO.input("GPIO1_28"):
			qtime = time.time()
		elif time.time() - qtime < TENBITTIMES:
			continue
		else:
			synced = True

	buslock.release()




    
def getmsg(busport,buslock):
	finished = False
	msg = []
	buslock.acquire()
	ttimeout = busport.timeout
	busport.timeout = TENBITTIMES
	tempb = b''
        #periodically timeout and let a blocking sender go.
	while tempb is b'':
		tempb = busport.read(1)
		if tempb is b'':
			buslock.release()
			buslock.acquire()
	msg += [tempb]
	busport.timeout = 0
	stime = time.time()
	
	while not finished:
		a = busport.read(1)
		t = time.time()
		if a is b'' and t - stime > TENBITTIMES:
			finished = True
		elif a is b'':
			continue
		else:
			stime = t
			msg += [a]

	busport.timeout=ttimeout
	buslock.release()
	if len(msg) <= 1 or not check(msg[:-1]) + toSignedChar(msg[-1]) == 0:
#		initialize(busport,buslock)
		return None
	else:
		return msg

    #msgqueue: a list type to enqueue messages
    #queuelock: a lock object that controls access to the queue
def run(busport,buslock,p):
	initialize(busport,buslock)
	while True:
		thismsg = getmsg(busport,buslock)
		if thismsg is not None:
			p.send(thismsg)
#test
#    def __init__(self,busport=None,buslock=None,msglock=None,msgqueue=None):
class J1708():
	def __init__(self,uart=None):
		self._sport = None
		if uart is not None:
			self._sport = serial.Serial(port=uart,baudrate=9600,
						    bytesize=serial.EIGHTBITS,
						    stopbits=serial.STOPBITS_ONE)

		self.buslock = Lock()
		self.mypipe, self.otherpipe = Pipe()
		self.r_proc = Process(target=run, args=(self._sport,self.buslock,self.otherpipe))
		self.r_proc.start()


	def read_message(self,timeout=None):
		if not self.mypipe.poll(timeout):
			return None

		retval = self.mypipe.recv()

		return list(retval)

    #currently relying on the read_thread to maintain synchronization
	def send_message(self,msg):
		retval = 0
		thismsg = bytes(msg)
		chksum = struct.pack('b',checksum(thismsg))
		thismsg += chksum
		with self.buslock:
			retval = self._sport.write(thismsg)
#			initialize(self._sport,self.buslock)
		return retval

	#cheater method for porting existing RP1210 code where the first byte of the buffer is the priority
	#however we don't care about priority really so just ignore the first byte
	def rp1210_send_message(self,msg):
		return self.send_message(msg[1:])

	def rp1210_read_message(self,timeout=None):
		return [0xde,0xad,0xbe,0xef]+self.read_message(timeout=timeout)
     
	def __del__(self):
		self.r_proc.terminate()


if __name__ == "__main__":
	thisport = J1708("/dev/ttyO2")
	
	count = 0
	while count < 50:
		a = thisport.read_message()
		if a is not None:
			print(a)
			#print(list(map(hex,a)))
		count += 1

	thisport.send_message([0xac,0xfe,0x80,0xf0,0x17])
	count = 0
	while count < 50:
		a = thisport.read_message()
		if a is not None:
			#print(list(map(hex,a)))
                        print(a)
		count += 1

	del(thisport)
