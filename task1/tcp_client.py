import socket
import struct
import argparse
import random
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('client_log.txt'),
        logging.StreamHandler()
    ]
)

def recv_all(sock, n):
    data = b''
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("连接断开")
        data += chunk
    return data

def split_file(content, Lmin, Lmax, seed):
    random.seed(seed)
    chunks = []
    pos = 0
    total = len(content)
    while pos < total:
        remain = total - pos
        if remain <= Lmax:
            chunk_len = remain
        else:
            chunk_len = random.randint(Lmin, Lmax)
        chunks.append(content[pos:pos+chunk_len])
        pos += chunk_len
    return chunks

def main():
    parser = argparse.ArgumentParser(description='TCP Reverse Client')
    parser.add_argument('server_ip', help='服务器IP')
    parser.add_argument('server_port', type=int, help='服务器端口')
    parser.add_argument('file', help='要发送的文件路径')
    parser.add_argument('Lmin', type=int, help='最小块长度')
    parser.add_argument('Lmax', type=int, help='最大块长度')
    parser.add_argument('seed', type=int, help='随机种子')
    args = parser.parse_args()

    with open(args.file, 'r', encoding='ascii') as f:
        content = f.read()
    logging.info(f"文件总长度: {len(content)} 字节")

    chunks = split_file(content, args.Lmin, args.Lmax, args.seed)
    N = len(chunks)
    logging.info(f"分块数 N = {N}")
    logging.info(f"分块完成: N={N}, 各块长度={[len(c) for c in chunks]}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((args.server_ip, args.server_port))
    logging.info(f"已连接到 {args.server_ip}:{args.server_port}")

    init_pkt = struct.pack('!HI', 1, N)
    sock.send(init_pkt)
    logging.info(f"发送 Initialization: N={N}")

    agree_data = recv_all(sock, 2)
    agree_type, = struct.unpack('!H', agree_data)
    if agree_type != 2:
        logging.info("未收到正确的 Agree 报文")
        sys.exit(1)
    logging.info("收到 Agree 报文")

    reversed_pieces = []
    for i, chunk in enumerate(chunks):
        req_header = struct.pack('!HI', 3, len(chunk))
        req_pkt = req_header + chunk.encode()
        sock.send(req_pkt)
        logging.info(f"发送 reverseRequest #{i+1}: 长度={len(chunk)}")

        ans_header = recv_all(sock, 6)
        ans_type, ans_len = struct.unpack('!HI', ans_header)
        if ans_type != 4:
            logging.info(f"第{i+1}块收到错误的报文类型")
            sys.exit(1)

        reversed_data = recv_all(sock, ans_len).decode()
        reversed_pieces.append(reversed_data)
        logging.info(f"收到 reverseAnswer #{i+1}: {reversed_data}")
        logging.info(f"收到 reverseAnswer #{i+1}: 反转后长度={ans_len}")

    output_file = "reversed_output.txt"
    reversed_pieces=reversed_pieces[::-1];
    with open(output_file, 'w', encoding='ascii') as f:
        f.write(''.join(reversed_pieces))
    logging.info(f"完整反转文件已保存至 {output_file}")

    sock.close()
    logging.info("客户端关闭")

if __name__ == '__main__':
    main()