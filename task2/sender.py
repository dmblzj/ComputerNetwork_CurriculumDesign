import time
import socket
import random
import protocol as proto
from stats import RTTStats, LossStats
from logger import setup_logger


class GBNSender:
    def __init__(self, sock, dest_addr, src_port, dst_port,
                 window_bytes=400, data_min=40, data_max=80, timeout=0.3,initial_seq=0):
        self.sock = sock
        self.dest_addr = dest_addr
        self.src_port = src_port
        self.dst_port = dst_port
        self.window_bytes = window_bytes
        self.data_min = data_min
        self.data_max = data_max
        self.timeout = timeout

        self.base = initial_seq
        self.next_seq = initial_seq
        self.packets = {}

        self.rtt_stats = RTTStats()
        self.loss_stats = LossStats()
        self.logger = setup_logger('sender', 'client_log.txt')

    def send_data(self, file_data):
        offset = 0
        total = len(file_data)

        while self.base < self.next_seq or offset < total:
            while self._window_not_full() and offset < total:
                chunk_size = random.randint(self.data_min, self.data_max)
                chunk_size = min(chunk_size, total - offset)
                chunk = file_data[offset:offset + chunk_size].encode()
                self._send_packet(self.next_seq, chunk)
                self.packets[self.next_seq] = (chunk, time.time())
                self.next_seq += 1
                offset += chunk_size
                self.loss_stats.record_send(is_new_packet=True)

            self._wait_for_ack()

        self.logger.info(f"发送完成: 总发送={self.loss_stats.total_sent}, "
                         f"丢包率={self.loss_stats.get_loss_rate():.2%}")

    def _window_not_full(self):
        sent_bytes = sum(len(self.packets[s][0]) for s in range(self.base, self.next_seq) if s in self.packets)
        return sent_bytes < self.window_bytes

    def _send_packet(self, seq, data):
        packet = proto.make_packet(
            src_ip='0.0.0.0', dst_ip=self.dest_addr[0],
            src_port=self.src_port, dst_port=self.dest_addr[1],
            seq=seq, ack=0, flags=proto.FLAG_DATA | proto.FLAG_ACK,
            student_id=0, data=data
        )
        self.sock.sendto(packet, self.dest_addr)
        self.loss_stats.record_send(is_new_packet=False)
        self.rtt_stats.record_send(seq)
        self.logger.info(f"发送 DATA: seq={seq}, len={len(data)}")

    def _wait_for_ack(self):
        self.sock.settimeout(self.timeout)
        try:
            data, _ = self.sock.recvfrom(2048)
            self._handle_ack(data)
        except socket.timeout:
            self._retransmit_all()

    def _handle_ack(self, packet):
        result = proto.parse_packet(self.dest_addr[0], '0.0.0.0', packet)
        if not result:
            return
        _, _, seq, ack, flags, _, _ = result
        if flags == proto.FLAG_ACK:
            if ack > self.base:
                # 正常情况：滑动窗口
                rtt = self.rtt_stats.record_ack(self.base)
                self.base = ack
                for s in list(self.packets.keys()):
                    if s < ack:
                        del self.packets[s]
            elif ack == self.base:
                pass

    def _retransmit_all(self):
        self.logger.warning(f"超时重传: base={self.base}, next={self.next_seq}")
        for seq in range(self.base, self.next_seq):
            if seq in self.packets:
                data, _ = self.packets[seq]
                self._send_packet(seq, data)

    def get_stats(self):
        return self.rtt_stats, self.loss_stats