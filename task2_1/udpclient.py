import socket
import struct
import random
import time
import argparse
import sys
import datetime
import pandas as pd

# ========== 协议常量 ==========
FLAG_SYN = 0x01
FLAG_ACK = 0x02
FLAG_FIN = 0x04
FLAG_DATA = 0x08

# 请将这里的 2704 换成你真实的学号后四位
STUDENT_ID_LAST4 = 2704
STUDENT_ID = STUDENT_ID_LAST4 ^ 0x5A3C


# ========== 校验和计算 ==========
def calculate_checksum(data):
    # 修复：处理长度为奇数的情况
    if len(data) % 2 != 0:
        data += b'\x00'
    total = 0
    for i in range(0, len(data), 2):
        word = (data[i] << 8) + data[i + 1]
        total += word
        while total > 0xFFFF:
            total = (total & 0xFFFF) + (total >> 16)
    return (~total) & 0xFFFF


def calculate_checksum_with_pseudo(src_ip, dst_ip, udp_packet):
    src_bytes = socket.inet_aton(src_ip)
    dst_bytes = socket.inet_aton(dst_ip)
    # 伪首部: 源IP, 目的IP, 置0, 协议号(UDP=17), UDP长度
    pseudo_header = struct.pack('!4s4sBBH', src_bytes, dst_bytes, 0, 17, len(udp_packet))
    return calculate_checksum(pseudo_header + udp_packet)


def make_packet(src_ip, dst_ip, src_port, dst_port, seq, ack, flags, student_id, data=b''):
    length = len(data)
    # 报文头 20 字节: src_port(2), dst_port(2), seq(4), ack(4), flags(1), student_id(2), len(2), reserved(1), checksum(2)
    temp_header = struct.pack('!HHIIBHHBH',
                              src_port, dst_port, seq, ack,
                              flags, student_id, length, 0, 0)
    temp_packet = temp_header + data
    checksum = calculate_checksum_with_pseudo(src_ip, dst_ip, temp_packet)
    header = struct.pack('!HHIIBHHBH',
                         src_port, dst_port, seq, ack,
                         flags, student_id, length, 0, checksum)
    return header + data


def parse_packet(src_ip, dst_ip, packet):
    if len(packet) < 20:
        return None
    (src_port, dst_port, seq, ack,
     flags, student_id, length, reserved, checksum) = struct.unpack('!HHIIBHHBH', packet[:20])

    if len(packet) < 20 + length:
        return None

    temp_packet = packet[:18] + b'\x00\x00' + packet[20:]
    calc = calculate_checksum_with_pseudo(src_ip, dst_ip, temp_packet)
    if checksum != calc:
        return None

    data = packet[20:20 + length]
    return (src_port, dst_port, seq, ack, flags, student_id, data)


# ========== 日志记录 ==========
def log_event(message):
    # 记录到 run_log.txt 中，时间戳格式尽量与 wireshark 对应
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    log_msg = f"[{timestamp}] {message}"
    with open('run_log.txt', 'a', encoding='utf-8') as f:
        f.write(log_msg + '\n')


# ========== 三次握手 ==========
def client_handshake(server_ip, server_port, local_port, timeout=1.0, max_retries=3):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', local_port))
    sock.settimeout(timeout)
    client_seq = random.randint(0, 10000)

    syn_packet = make_packet('127.0.0.1', server_ip, local_port, server_port,
                             client_seq, 0, FLAG_SYN, STUDENT_ID)

    for _ in range(max_retries):
        print(f"发送 SYN 请求连接, seq={client_seq}")
        log_event(f"发送 SYN, seq={client_seq}, student_id={STUDENT_ID}")
        sock.sendto(syn_packet, (server_ip, server_port))
        try:
            data, _ = sock.recvfrom(2048)
            result = parse_packet(server_ip, '127.0.0.1', data)
            if result:
                _, _, seq, ack, flags, _, _ = result
                if flags == (FLAG_SYN | FLAG_ACK) and ack == client_seq + 1:
                    server_seq = seq
                    ack_packet = make_packet('127.0.0.1', server_ip, local_port, server_port,
                                             client_seq + 1, server_seq + 1, FLAG_ACK, 0)
                    sock.sendto(ack_packet, (server_ip, server_port))
                    print("握手成功，连接建立！")
                    log_event("握手成功")
                    return sock, client_seq + 1
        except socket.timeout:
            print("握手超时，正在重试...")
            log_event("握手超时，重传 SYN")
            continue
    sock.close()
    return None, 0


# ========== GBN 发送逻辑 ==========
class GBNSender:
    def __init__(self, sock, dest_addr, src_port, dst_port, initial_seq):
        self.sock = sock
        self.dest_addr = dest_addr
        self.src_port = src_port
        self.dst_port = dst_port

        self.window_bytes = 400  # 窗口大小 400 字节
        self.packet_size = 80  # 每个数据包 80 字节
        self.timeout = 0.3  # 超时时间 300ms

        self.base = initial_seq
        self.next_seq = initial_seq
        self.packets = {}  # 缓冲区

        self.total_sent = 0  # 总发包数(含重传)
        self.rtts = []  # 记录往返时间
        self.next_packet_num = 1  # 记录这是第几个包

    def send_30_packets(self):
        # 生成测试数据：30个包 * 80字节 = 2400 字节
        total_packets_to_send = 30
        file_data = b"X" * (total_packets_to_send * self.packet_size)
        total_len = len(file_data)
        offset = 0

        # 清空/创建日志文件
        open('run_log.txt', 'w').close()

        print("\n--- 开始数据传输 ---")
        while self.base < self.next_seq or offset < total_len:
            # 1. 窗口未满且还有数据，发送新数据
            while (self.next_seq - self.base) < self.window_bytes and offset < total_len:
                chunk = file_data[offset:offset + self.packet_size]

                # 记录包的元数据，方便打印和重传
                start_byte = self.next_seq
                end_byte = self.next_seq + len(chunk) - 1
                pkt_num = self.next_packet_num

                self.packets[self.next_seq] = {
                    'chunk': chunk,
                    'n': pkt_num,
                    'x': start_byte,
                    'y': end_byte,
                    'send_time': time.time()
                }

                self._send_raw_packet(self.next_seq, chunk)
                print(f"第 {pkt_num} 个（第 {start_byte}~{end_byte} 字节）client 端已经发送")
                log_event(f"发送 DATA: 第 {pkt_num} 个（第 {start_byte}~{end_byte} 字节）")

                self.next_seq += len(chunk)
                offset += len(chunk)
                self.next_packet_num += 1
                self.total_sent += 1

            # 2. 等待 ACK
            self.sock.settimeout(self.timeout)
            try:
                data, _ = self.sock.recvfrom(2048)
                self._handle_ack(data)
            except socket.timeout:
                self._retransmit_all()

    def _send_raw_packet(self, seq, data):
        packet = make_packet('127.0.0.1', self.dest_addr[0],
                             self.src_port, self.dest_addr[1],
                             seq, 0, FLAG_DATA | FLAG_ACK, 0, data)
        self.sock.sendto(packet, self.dest_addr)

    def _handle_ack(self, packet):
        result = parse_packet(self.dest_addr[0], '127.0.0.1', packet)
        if not result: return
        _, _, _, ack, flags, _, _ = result

        if flags == FLAG_ACK and ack > self.base:
            # 累积确认：清理被确认的包
            for seq in list(self.packets.keys()):
                if seq < ack:
                    pkt = self.packets[seq]
                    rtt_ms = (time.time() - pkt['send_time']) * 1000
                    self.rtts.append(rtt_ms)

                    print(f"第 {pkt['n']} 个（第 {pkt['x']}~{pkt['y']} 字节）server 端已经收到，RTT 是 {rtt_ms:.2f} ms")
                    log_event(f"收到 ACK: 第 {pkt['n']} 个包已确认, RTT={rtt_ms:.2f}ms")

                    del self.packets[seq]
            self.base = ack

    def _retransmit_all(self):
        # GBN 超时重传窗口内的所有包
        log_event(f"发生超时，准备重传")
        for seq in sorted(self.packets.keys()):
            pkt = self.packets[seq]
            self._send_raw_packet(seq, pkt['chunk'])
            # 重传时重置发送时间，以便重新计算RTT（简单处理）
            pkt['send_time'] = time.time()
            self.total_sent += 1

            print(f"重传第 {pkt['n']} 个（第 {pkt['x']}~{pkt['y']} 字节）数据包")
            log_event(f"超时重传 DATA: 第 {pkt['n']} 个（第 {pkt['x']}~{pkt['y']} 字节）")

    def print_summary(self):
        print("\n【 汇 总 】")
        # 丢包率 = 1 - (30 / 实际发送总包数)
        # 任务书要求：按 “30÷实际发送的 udp packet number” 计算，这里实际算是成功率，做一下转换
        actual_sent = self.total_sent
        loss_rate = (1 - (30 / actual_sent)) * 100 if actual_sent > 0 else 100

        print(f"丢包率: {loss_rate:.2f}% (计算公式: 1 - 30÷{actual_sent})")
        log_event(f"统计汇总 -> 总发送数: {actual_sent}, 丢包率: {loss_rate:.2f}%")

        if self.rtts:
            # 必须使用 pandas 进行统计
            s = pd.Series(self.rtts)
            print(f"整个过程中的最大 RTT: {s.max():.2f} ms")
            print(f"整个过程中的最小 RTT: {s.min():.2f} ms")
            print(f"整个过程中的平均 RTT: {s.mean():.2f} ms")
            print(f"RTT 的标准差:       {s.std():.2f} ms")
        else:
            print("没有成功记录到 RTT。")


# ========== 主程序 ==========
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('server_ip', help='服务器IP地址')
    parser.add_argument('server_port', type=int, help='服务器端口号')
    args = parser.parse_args()

    local_port = random.randint(10000, 60000)
    sock, initial_seq = client_handshake(args.server_ip, args.server_port, local_port)

    if not sock:
        print("三次握手建立连接失败，程序退出。")
        sys.exit(1)

    sender = GBNSender(sock, (args.server_ip, args.server_port), local_port, args.server_port, initial_seq)
    sender.send_30_packets()
    sender.print_summary()

    sock.close()


if __name__ == '__main__':
    main()