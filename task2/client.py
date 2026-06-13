import sys
import argparse
from handshake import client_handshake
from sender import GBNSender


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('server_ip')
    parser.add_argument('server_port', type=int)
    parser.add_argument('file')
    parser.add_argument('--timeout', type=float, default=0.3)
    args = parser.parse_args()

    with open(args.file, 'r', encoding='ascii') as f:
        content = f.read()

    sock, client_seq, server_seq, ok = client_handshake(
        args.server_ip, args.server_port, local_port=12345, timeout=1.0
    )
    if not ok:
        print("握手失败")
        sys.exit(1)

    sender = GBNSender(sock, (args.server_ip, args.server_port),
                       src_port=12345, dst_port=args.server_port,
                       timeout=args.timeout,
                       initial_seq=client_seq + 1)
    sender.send_data(content)

    rtt_stats, loss_stats = sender.get_stats()
    rtt_stats.print_stats()
    print(f"丢包率: {loss_stats.get_loss_rate():.2%}")

    sock.close()


if __name__ == '__main__':
    main()