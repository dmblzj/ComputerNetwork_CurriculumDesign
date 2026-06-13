import socket
import struct
import random
import argparse

# ========== 协议常量 ==========
FLAG_SYN = 0x01
FLAG_ACK = 0x02
FLAG_FIN = 0x04
FLAG_DATA = 0x08


# ========== 校验和计算 (同Client) ==========
def calculate_checksum(data):
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
    pseudo_header = struct.pack('!4s4sBBH', src_bytes, dst_bytes, 0, 17, len(udp_packet))
    return calculate_checksum(pseudo_header + udp_packet)


def make_packet(src_ip, dst_ip, src_port, dst_port, seq, ack, flags, student_id, data=b''):
    length = len(data)
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
    if len(packet) < 20: return None
    (src_port, dst_port, seq, ack,
     flags, student_id, length, reserved, checksum) = struct.unpack('!HHIIBHHBH', packet[:20])

    if len(packet) < 20 + length: return None
    temp_packet = packet[:18] + b'\x00\x00' + packet[20:]
    calc = calculate_checksum_with_pseudo(src_ip, dst_ip, temp_packet)

    if checksum != calc: return None
    data = packet[20:20 + length]
    return (src_port, dst_port, seq, ack, flags, student_id, data)


# ========== 主程序与 Server 逻辑 ==========
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('server_ip', help='绑定IP (通常用 0.0.0.0)')
    parser.add_argument('port', type=int, help='绑定端口')
    parser.add_argument('loss_rate', type=float, help='丢包率 (0.0 到 1.0)')
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((args.server_ip, args.port))
    print(f"Server 启动在 {args.server_ip}:{args.port}，模拟丢包率设定为 {args.loss_rate * 100}%")

    # 字典记录不同 Client 的状态，避免多线程抢夺 socket
    # 格式: client_addr -> {'expected_seq': int}
    clients = {}

    while True:
        try:
            packet, addr = sock.recvfrom(2048)
            server_ip = '127.0.0.1'  # 本地测试可以固定，如果是公网需获取真实IP
            client_ip = addr[0]

            result = parse_packet(client_ip, server_ip, packet)
            if not result:
                continue

            src_port, dst_port, seq, ack, flags, student_id, data = result

            # 1. 握手阶段 (收到 SYN)
            if flags == FLAG_SYN:
                # 强制要求：Server 收到连接请求时，须验证字段是否符合 XOR 规则！
                verify_num = student_id ^ 0x5A3C
                if 0 <= verify_num <= 9999:
                    print(f"[{addr}] 收到 SYN 握手请求，学号校验成功 (结果: {verify_num})")
                    client_seq = seq
                    server_seq = random.randint(0, 10000)

                    syn_ack = make_packet(server_ip, client_ip, args.port, src_port,
                                          server_seq, client_seq + 1,
                                          FLAG_SYN | FLAG_ACK, 0)
                    sock.sendto(syn_ack, addr)

                    # 记录该客户端期待接收的下一个字节序号 (按 TCP 机制，建立连接后数据从 seq+1 开始)
                    clients[addr] = {'expected_seq': client_seq + 1}
                else:
                    print(f"[{addr}] 拒绝连接，StudentID 校验不合法 (结果: {verify_num})")

            # 2. 数据传输阶段 (收到 DATA)
            elif flags & FLAG_DATA:
                if addr not in clients:
                    continue  # 未建立连接的包直接忽略

                expected_seq = clients[addr]['expected_seq']

                # 模拟随机丢包
                if random.random() < args.loss_rate:
                    print(f"[{addr}] [丢包模拟] 故意丢弃序列号 seq={seq} 的数据包")
                    continue

                # 检查序号是否是期望的 (GBN 按序接收)
                if seq == expected_seq:
                    print(f"[{addr}] 收到按序 DATA，seq={seq}，长度={len(data)}")
                    # 序号推进
                    clients[addr]['expected_seq'] += len(data)
                else:
                    print(f"[{addr}] 收到失序 DATA，期望 seq={expected_seq}，实际 seq={seq}。发送冗余 ACK")

                # 无论是否按序，都回复累计确认（期望收到的下一个序号）
                ack_packet = make_packet(server_ip, client_ip, args.port, src_port,
                                         0, clients[addr]['expected_seq'],
                                         FLAG_ACK, 0)
                sock.sendto(ack_packet, addr)

            # (如果收到第三次握手的纯ACK，可在这里处理，不过因为我们基于 UDP 无连接，目前状态可以直接忽略纯 ACK)

        except KeyboardInterrupt:
            print("\n服务器关闭")
            break
        except Exception as e:
            print(f"发生错误: {e}")


if __name__ == '__main__':
    main()