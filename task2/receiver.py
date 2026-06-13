import protocol as proto
from logger import setup_logger


class GBNReceiver:
    def __init__(self, expected_seq=0, loss_rate=0.0):
        self.expected_seq = expected_seq
        self.received_data = []
        self.loss_rate = loss_rate
        self.logger = setup_logger('receiver', 'server_log.txt')

    def handle_packet(self, packet, addr, sock):
        result = proto.parse_packet(addr[0], '0.0.0.0', packet)
        if not result:
            return False

        src_port, dst_port, seq, ack, flags, student_id, data = result

        if not (flags & proto.FLAG_DATA):
            return False

        # 丢包模拟
        import random
        if random.random() < self.loss_rate:
            self.logger.warning(f"丢包: 丢弃 DATA seq={seq}")
            return False

        if seq == self.expected_seq:
            self.received_data.append(data)
            self.logger.info(f"接收 DATA: seq={seq}, len={len(data)}")
            self.expected_seq += len(data)
            self._send_ack(sock, addr, dst_port, src_port)
            return True
        else:
            self.logger.info(f"失序: 期望 seq={self.expected_seq}, 收到 seq={seq}")
            self._send_ack(sock, addr, dst_port, src_port)
            return False

    def _send_ack(self, sock, addr, src_port, dst_port):
        ack_packet = proto.make_packet(
            src_ip='0.0.0.0', dst_ip=addr[0],
            src_port=dst_port, dst_port=src_port,
            seq=0, ack=self.expected_seq,
            flags=proto.FLAG_ACK, student_id=0, data=b''
        )
        sock.sendto(ack_packet, addr)
        self.logger.info(f"发送 ACK: ack={self.expected_seq}")

    def get_data(self):
        return b''.join(self.received_data).decode()