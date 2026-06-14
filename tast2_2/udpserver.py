import random
import socket
import argparse
import logging
import threading

from TCP import TCP
# 常量
FLAG_SYN = 0x01
FLAG_ACK = 0x02
FLAG_DATA = 0x08
STUDENT_ID=2704 ^ 0x5A3C

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler("udpserver.txt"),   # 写入文件
        logging.StreamHandler()               # 输出到屏幕
    ]
)

#TCP (self,seq=0, ack=0, flags=0, student_id=0, length=0, data=b'')




def main():
    parser = argparse.ArgumentParser(
        description="Task2 Udp Socket Programming - Server",
        epilog="示例: python udpserver.py 8888"
    )
    parser.add_argument('server_port', type=int, help='服务器端口号')
    parser.add_argument('loss_rate', type=float, help='丢包率')
    args = parser.parse_args()

    udp_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_server.bind(('0.0.0.0', args.server_port))
    logging.info(f"服务器启动，监听端口 {args.server_port}...")

    data,addr=udp_server.recvfrom(2024)
    hand1 = TCP.tcp_decode(data)
    logging.info(f"收到来自客户端{addr}的握手1")
    seq_sta = random.randint(0, 10000)
    if hand1.flags == FLAG_SYN:
        if 0<hand1.student_id^ 0x5A3C<9999:
            logging.info("学号检验成功")
            hand2 = TCP(seq=seq_sta, ack=hand1.seq + 1, flags=FLAG_ACK | FLAG_SYN)
            udp_server.sendto(hand2.tcp_encode(), addr)
            logging.info(f"向{addr}发送握手2")
            data, _ = udp_server.recvfrom(2048)
            hand3 = TCP.tcp_decode(data)
            logging.info(f"收到来自客户端{addr}的握手3")
            hand3_back=TCP(seq=hand3.ack,ack=hand3.seq,flags=FLAG_ACK)
            udp_server.sendto(hand3_back.tcp_encode(),addr)
            logging.info("回复握手3")
        else:
            logging.info(f"拒绝连接{addr}，StudentID 校验不合法")
            return

    # TCP (self,seq=0, ack=0, flags=0, student_id=0, length=0, data=b'')
    expected_seq=hand1.seq + 1
    while True:
        data,addr=udp_server.recvfrom(2048)
        pkt=TCP.tcp_decode(data)
        if pkt.flags==FLAG_DATA:
            #模拟随机丢包
            if random.random()<args.loss_rate:
                logging.info(f"【模拟丢包】故意丢弃 seq={pkt.seq}")
                continue


            if pkt.seq==expected_seq:
                expected_seq=pkt.seq+80
                logging.info(f"收到按序包 seq={pkt.seq}, 期待下一个 {pkt.seq + 80}")
            else:
                logging.info(f"收到失序包 seq={pkt.seq}, 仍期待 {expected_seq}")

            ack_back=TCP(ack=expected_seq,flags=FLAG_ACK)
            udp_server.sendto(ack_back.tcp_encode(),addr)




if __name__ == '__main__':
    main()