import threading

def worker1():
    for x in range(1,2000):
        print('1: ' + str(x))

def worker2():
    for x in range(1,2000):
        print('2: ' + str(x))

t1 = threading.Thread(target=worker1)
t2 = threading.Thread(target=worker2)
t1.start()
t2.start()