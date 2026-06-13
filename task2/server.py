import argparse
import socket
from handshake import server_handshake
from receiver import GBNReceiver
import protocol as proto


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('server_ip', help='服务器IP')
    parser.add_argument('port', type=int, default=8888,help='服务器端口号')
    parser.add_argument('loss', type=float, default=0.2,help='丢包率')
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((args.server_ip, args.port))
    print(f"服务器启动，端口 {args.port}，丢包率 {args.loss * 100}%")

    result = server_handshake(sock, proto.STUDENT_ID)
    if not result:
        print("握手失败")
        return

    client_addr, client_seq, server_seq = result
    print(f"与 {client_addr} 握手完成")

    receiver = GBNReceiver(expected_seq=client_seq + 1, loss_rate=args.loss)

    while True:
        try:
            packet, addr = sock.recvfrom(2048)
            receiver.handle_packet(packet, addr, sock)
        except KeyboardInterrupt:
            break

    with open('received_file.txt', 'w', encoding='ascii') as f:
        f.write(receiver.get_data())
    print("文件已保存")


if __name__ == '__main__':
    main()