import socket
import struct
import threading
import logging


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('server_log.txt'),
        logging.StreamHandler()
    ]
)

def recv_all(sock, n):
    data = b''
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            logging.info("连接断开")
            raise ConnectionError("连接断开")
        data += chunk
    return data


def handle_client(conn, addr):
    logging.info(f"新连接来自 {addr}")

    try:
        # 接收 Initialization (6字节)
        header = recv_all(conn, 6)
        typ, N = struct.unpack('!HI', header)
        logging.info(f"收到 type={typ}, N={N}")
        if typ != 1:
            logging.info(f"非法报文类型 {typ}")
            conn.close()
            return
        logging.info(f"收到 Initialization: N={N}")

        # 发送 Agree (2字节)
        conn.send(struct.pack('!H', 2))
        logging.info("发送 Agree 报文")

        # 处理 N 个 reverseRequest
        for i in range(N):
            # 接收 reverseRequest 头部 (6字节)
            req_header = recv_all(conn, 6)
            typ, length = struct.unpack('!HI', req_header)
            if typ != 3:
                logging.info(f"期望 type=3，实际收到 {typ}")
                break

            # 接收数据
            data = recv_all(conn, length).decode()
            logging.info(f"收到第{i+1}块: {data}")

            # 反转
            reversed_str = data[::-1]

            # 发送 reverseAnswer
            ans_header = struct.pack('!HI', 4, len(reversed_str))
            conn.send(ans_header + reversed_str.encode())
            logging.info(f"处理第{i + 1}块: 原长度={length}, 反转后长度={len(reversed_str)}")
            logging.info(f"已回复第{i + 1}块")

        logging.info(f"[完成] {addr}")

    except Exception as e:
        logging.error(f"处理 {addr} 时出错: {e}")
    finally:
        conn.close()
        logging.info(f"断开连接 {addr}")


def main():
    HOST = '0.0.0.0'
    PORT = 8888;

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((HOST, PORT))
    server_sock.listen(5)
    logging.info(f"服务器启动，监听端口 {PORT}")

    while True:
        conn, addr = server_sock.accept()
        logging.info(f"接受连接: {addr}")
        threading.Thread(target=handle_client, args=(conn, addr)).start()


if __name__ == '__main__':
    main()