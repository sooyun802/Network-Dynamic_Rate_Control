from socket import *
import time
import threading
from threading import Lock

my_lock = Lock()


def message_rcv(seq_num, address):
    global minimumRTT, bottleneckQueueSize, queue, rcvSocket

    seq_num = seq_num.decode()
    tmp = seq_num.split('@', 1)
    seq_num = tmp[0]
    flag = False

    tmp = time.time()
    while True:
        if time.time() - tmp >= minimumRTT / 2.0:
            break

    with my_lock:
        if len(queue) < bottleneckQueueSize:        # queue has free space > ACK
            queue.append((int(seq_num), address))
        else:                                       # queue is full > NACK
            flag = True

    if flag:
        tmp = time.time()
        while True:
            if time.time() - tmp >= minimumRTT / 2.0:
                break
        rcvSocket.sendto(("NACK " + seq_num).encode(), address)


def dequeue():
    global bottleneckLinkRate, bottleneckQueueSize, queue, rcvSocket, base_time

    while True:
        if time.time() - base_time >= 1.0 / bottleneckLinkRate:
            base_time = time.time()

            with my_lock:
                if len(queue) > 0:
                    (seq_num, address) = queue[0]
                    del queue[0]
                    t_sendACK = threading.Thread(target=send_ack, args=(seq_num, address,))
                    t_sendACK.start()


def send_ack(seq_num, address):
    global minimumRTT, rcvSocket, ackCnt

    tmp = time.time()
    while True:
        if time.time() - tmp >= minimumRTT / 2.0:
            break

    with my_lock:
        ackCnt += 1
    rcvSocket.sendto(("ACK " + str(seq_num)).encode(), address)


def time_interval():
    global time_base, ackCnt, queue, bottleneckQueueSize

    cnt = 0
    queue_occupancy = 0
    init_time = time_base

    while True:
        tmp = time.time()
        if tmp - time_base >= 0.1:
            with my_lock:
                queue_occupancy += len(queue)
            cnt += 1

            if cnt == 20:
                with my_lock:
                    print("time: {0:0.2f}".format(tmp - init_time))
                    print("   - Receiving rate: {0:0.2f} pps".format(ackCnt / 2.0))
                    print("   - Average queue occupancy: {0:0.2f}%".format((queue_occupancy / 20.0) / bottleneckQueueSize * 100.0), end="\n\n")
                    # print("{0:0.2f}\t{1:0.2f}\t{2:0.2f}".format((tmp - init_time), (ackCnt / 2.0), \
                    #                                            (queue_occupancy / 20.0)))

                    ackCnt = 0

                cnt = 0
                queue_occupancy = 0

            time_base += 0.1


receiver = ('127.0.0.1', 12000)
minimumRTT = eval(input("Enter minimum RTT: "))
bottleneckLinkRate = eval(input("Enter bottleneck link rate (pps): "))
bottleneckQueueSize = eval(input("Enter bottleneck queue size (packets): "))
print("")

rcvSocket = socket(AF_INET, SOCK_DGRAM)
rcvSocket.bind(receiver)

t_dequeue = threading.Thread(target=dequeue, args=())
t_time = threading.Thread(target=time_interval, args=())

queue = []
ackCnt = 0
base_time = time.time()
time_base = base_time

t_dequeue.start()
t_time.start()

while True:
    msg, rcv_address = rcvSocket.recvfrom(2048)
    t_receive = threading.Thread(target=message_rcv, args=(msg, rcv_address,))
    t_receive.start()