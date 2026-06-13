import argparse
import socket
import threading
from handshake import server_handshake
from receiver import GBNReceiver
import protocol as proto


def handle_client(sock, client_addr, client_seq, server_seq, loss_rate):
    """处理单个客户端的数据传输"""
    print(f"[线程] 开始处理 {client_addr}")
    receiver = GBNReceiver(expected_seq=client_seq + 1, loss_rate=loss_rate)

    while True:
        try:
            packet, addr = sock.recvfrom(2048)
            if addr != client_addr:
                continue
            receiver.handle_packet(packet, addr, sock)
        except KeyboardInterrupt:
            break

    with open(f'received_{client_addr[1]}.txt', 'w', encoding='ascii') as f:
        f.write(receiver.get_data())
    print(f"[线程] {client_addr} 文件已保存")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('server_ip', help='服务器IP')
    parser.add_argument('port', type=int, default=8888, help='服务器端口号')
    parser.add_argument('loss', type=float, default=0.2, help='丢包率')
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((args.server_ip, args.port))
    print(f"服务器启动，端口 {args.port}，丢包率 {args.loss * 100}%")

    while True:
        # 每次握手后，新开一个线程处理该客户端
        result = server_handshake(sock, proto.STUDENT_ID)
        if not result:
            print("握手失败，继续等待")
            continue

        client_addr, client_seq, server_seq = result
        print(f"与 {client_addr} 握手完成")

        thread = threading.Thread(
            target=handle_client,
            args=(sock, client_addr, client_seq, server_seq, args.loss),
            daemon=True
        )
        thread.start()
        print(f"当前活跃客户端数: {threading.active_count() - 1}")


if __name__ == '__main__':
    main()