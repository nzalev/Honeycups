from multiprocessing import Pipe
import threading
import logging
import signal
import socket
import queue
import grp
import pwd
import sys
import os


class DataLogger(threading.Thread):
    def __init__(self, parent: 'HoneypotServer') -> None:
        super().__init__()
        self.parent = parent
        self.datalog = open('/home/honeycups/connslog', 'a')

    def run(self) -> None:
        while (not self.parent.quitting):
            try:
                msg, addr = \
                    self.parent.message_queue.get(block=True, timeout=1)
                self.datalog.write('{}: {}\n'.format(addr[0], msg))
                self.datalog.flush()

            except queue.Empty:
                pass

            except Exception as e:
                logging.exception(
                    'DataLogger encountered unhandled exception')


class HoneypotServer():
    def __init__(self, pipe) -> None:
        os.environ['HOME'] = '/home/honeycups'
        self.setup_logger()

        signal.signal(signal.SIGTERM, self.sigterm_handler)

        self.message_queue = queue.Queue()
        self.quitting = False

        try:
            logging.debug('binding sockets ...')
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind(('0.0.0.0', 631))
        except Exception as e:
            logging.exception('failed to bind socket. exiting ...')
            pipe.send(1)
            exit(1)

        try:
            logging.debug('dropping privileges ...')
            self.drop_privileges()
        except Exception as e:
            logging.exception('failed to drop root privileges. exiting ...')
            pipe.send(1)
            exit(1)

        logging.debug('spawning data logger ...')
        self.logging_handler = DataLogger(self)
        self.logging_handler.daemon = True
        self.logging_handler.start()

        pipe.send(0)

    def drop_privileges(self) -> None:
        uid = pwd.getpwnam('honeycups').pw_uid
        gid = grp.getgrnam('honeycups').gr_gid
        os.setgroups([])
        os.setgid(gid)
        os.setuid(uid)

    def setup_logger(self) -> None:
        filename = os.environ['HOME'] + '/honeycups.log'
        format='%(asctime)s %(levelname)s\t%(message)s'
        logging.basicConfig(filename=filename,
                            encoding='utf-8',
                            level='DEBUG',
                            format=format)

    def sigterm_handler(self, signo, stack_frame) -> None:
        self.graceful_exit()

    def graceful_exit(self) -> None:
            logging.info('interrupt received. exiting ...')
            self.quitting = True
            self.logging_handler.join()
            self.socket.close()
            exit(0)

    def receive_connections(self) -> None:
        try:
            while True:
                msg, addr = self.socket.recvfrom(4096)
                self.message_queue.put((msg, addr))

        except KeyboardInterrupt as e:
            self.graceful_exit()



parent_pipe, child_pipe = Pipe()

if ((pid := os.fork()) == 0):
    svr = HoneypotServer(child_pipe)
    svr.receive_connections()
else:
    code = parent_pipe.recv()
    exit(code)
