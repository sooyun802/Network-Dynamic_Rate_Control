from socket import *
import time
import threading
import sys
from threading import Lock

my_lock = Lock()


def time_interval():
    global sendingRate, averageRTT, nackFlag, ackCnt, base_time

    init_time = base_time

    while True:
        tmp = time.time()
        if tmp - base_time >= 2:
            with my_lock:
                print("time: {0:0.2f}".format(tmp - init_time))
                print("   - Average RTT: {0:0.2f} sec".format(averageRTT))
                print("   - Sending Rate: {0:0.2f} pps".format(sendingRate))
                print("   - Goodput: {0:0.2f} pps".format(ackCnt / 2.0), end="\n\n")
                # print("{0:0.2f}\t{1:0.2f}\t{2:0.02f}\t{3:0.2f}".format((tmp - init_time), averageRTT, sendingRate, \
                #                                                       (ackCnt / 2.0)))

                base_time = base_time + 2.0 # update base time (to count 2 sec)
                nackFlag = True
                ackCnt = 0


def listener():
    global sendingRate, sendingInterval, averageRTT, pktSndTime, nackFlag, ackCnt

    while True:
        msg, rcv_address = sndSocket.recvfrom(2048)
        tmp = time.time()
        msg = msg.decode().split(' ')   # msg[0]: ACK/NACK, msg[1]: seq#

        with my_lock:
            if msg[0] == "NACK":
                if nackFlag:    # first NACK in 2 sec window
                    nackFlag = False
                    sendingRate /= 2.0
                    sendingInterval = 1.0 / sendingRate

            else:   # msg[0] == "ACK"
                ackCnt += 1
                sendingRate = sendingRate + 1.0 / sendingRate
                sendingInterval = 1.0 / sendingRate

                # update average RTT
                if averageRTT == 0:
                    averageRTT = (tmp - pktSndTime[int(msg[1])])
                else:
                    averageRTT = 0.875 * averageRTT + 0.125 * (tmp - pktSndTime[int(msg[1])])

        del pktSndTime[int(msg[1])]


receiver = ('127.0.0.1', 12000)
sendingRate = eval(input("Enter initial sending rate (pps): "))
print("")

sendingInterval = 1.0 / sendingRate
seqNum = 0
averageRTT = 0
nackFlag = True
ackCnt = 0
pktSndTime = {}

sndSocket = socket(AF_INET, SOCK_DGRAM)
sndSocket.bind(('127.0.0.1', 0))

t_listener = threading.Thread(target=listener, args=())
t_time = threading.Thread(target=time_interval, args=())

snd_time = 0
base_time = time.time()

t_listener.start()
t_time.start()

while True:
    tmp = time.time()
    with my_lock:
        if tmp - snd_time >= sendingInterval:
            sendMsg = str(seqNum)
            while sys.getsizeof(sendMsg) < 1000:
                sendMsg += "@"
            sndSocket.sendto(str(seqNum).encode(), receiver)
            pktSndTime[seqNum] = tmp

            seqNum += 1
            snd_time = tmp
