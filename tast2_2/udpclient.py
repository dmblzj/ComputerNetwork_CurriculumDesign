import random
import socket
import argparse
import logging
import threading
import time
import pandas as pd

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
        logging.FileHandler("udpclient.txt"),   # 写入文件
        logging.StreamHandler()               # 输出到屏幕
    ]
)

#TCP (self,seq=0, ack=0, flags=0, student_id=0, length=0, data=b'')
base=0
next_seq=0
window_size=400
packet_size=80
lock=threading.Lock()
seq_sta=random.randint(0,10000)
time_lit=0.3
total_sent_count = 0

rtt_list=[]
send_times={}

packets = []
for i in range(30):
    data = f"PacketContent-{i+1:02}".encode().ljust(80, b'X') # 凑够80字节
    seq = (seq_sta + 1) + (i * 80)
    packets.append({'seq': seq, 'data': data, 'num': i + 1})
seq_last=seq_sta+30*80

def receive_thread(udp_socket):
    global base,rtt_list
    while base<seq_last:
        data,_=udp_socket.recvfrom(2048)
        ack_pkt=TCP.tcp_decode(data)

        if ack_pkt and ack_pkt.flags==FLAG_ACK:
            with lock:
                if ack_pkt.ack>base:
                    if base in send_times:
                        rtt = (time.time() - send_times[base]) * 1000
                        rtt_list.append(rtt)
                        logging.info(f"收到 ACK={ack_pkt.ack}, RTT={rtt:.2f}ms")
                    base=ack_pkt.ack
                    #logging.info(f"base 已更新为 {base}")



def main():
    global base,next_seq,window_size,packet_size,lock,seq_sta,total_sent_count
    parser=argparse.ArgumentParser(
        description="Task2 Udp Socket Programming",
        epilog="示例: python udpclient.py 192.168.1.100 8888"
    )
    parser.add_argument('server_ip', help='服务器IP地址')
    parser.add_argument('server_port', type=int, help='服务器端口号')
    args=parser.parse_args()
    udp_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #三次握手
    udp_client.settimeout(2.0)
    addr=(args.server_ip,args.server_port)

    hand1=TCP(seq_sta,0,FLAG_SYN,STUDENT_ID,0)

    connected = False
    for i in range(3):
        try:
            udp_client.sendto(hand1.tcp_encode(), addr)
            logging.info(f"向服务端发送握手1 (SYN), seq={seq_sta}")

            data, _ = udp_client.recvfrom(2048)
            hand2 = TCP.tcp_decode(data)

            if hand2 and hand2.flags == (FLAG_ACK | FLAG_SYN) and hand2.ack == seq_sta + 1:
                logging.info(f"收到服务器握手2 (SYN+ACK), server_seq={hand2.seq}")

                hand3 = TCP(seq=hand2.ack, ack=hand2.seq + 1, flags=FLAG_ACK)
                udp_client.sendto(hand3.tcp_encode(), addr)
                logging.info(f"向服务端发送握手3 , seq={seq_sta+1}")
                logging.info("三次握手完成，连接已建立")
                data,_=udp_client.recvfrom(2048)
                hand3_back=TCP.tcp_decode(data)
                connected = True
                break
        except socket.timeout:
            logging.info(f"握手超时，正在进行第 {i + 2} 次重试...")

    if not connected:
        logging.info("连接服务器失败")
        return


    #数据传输阶段
    udp_client.settimeout(None)
    base = seq_sta + 1
    next_seq = seq_sta + 1
    t = threading.Thread(target=receive_thread, args=(udp_client,))
    t.daemon = True
    t.start()

    base = seq_sta + 1
    next_seq = seq_sta + 1

    while base < seq_last:
        repeat=False
        with lock:

            if next_seq<base:
                next_seq=base

            # 正常发送窗口内的包
            if next_seq < base + window_size and (next_seq - (seq_sta + 1)) // 80 < 30:
                idx = (next_seq - (seq_sta + 1)) // 80
                pkt = packets[idx]

                out_pkt = TCP(seq=pkt['seq'], flags=FLAG_DATA, data=pkt['data'])
                udp_client.sendto(out_pkt.tcp_encode(), addr)
                total_sent_count += 1


                if next_seq not in send_times:
                    send_times[next_seq] = time.time()

                logging.info(f"第 {pkt['num']} 个（第 {next_seq}~{next_seq + 79} 字节）client端已经发送")
                next_seq += 80

            # 检查是否超时
            if base in send_times and (time.time() - send_times[base] > time_lit):
                logging.info(f"超时！回退N帧，从 seq={base} 开始重传")
                repeat=True
                # 重传所有未确认的包
                curr = base
                while curr < next_seq:
                    idx = (curr - (seq_sta + 1)) // 80
                    if idx < len(packets):
                        pkt = packets[idx]
                        out_pkt = TCP(seq=pkt['seq'], flags=FLAG_DATA, data=pkt['data'])
                        udp_client.sendto(out_pkt.tcp_encode(), addr)
                        total_sent_count+=1
                        #重置计时器
                        send_times[curr] = time.time()
                        logging.info(f"重传 第 {pkt['num']} 个包 (seq={curr})")
                    curr += 80
                #更新next_seq
                next_seq = base
                #time.sleep(time_lit)


        if repeat==True:
            time.sleep(time_lit//2)

        time.sleep(0.01)

    if rtt_list:
        df = pd.Series(rtt_list)
        print("\n【 数据传输汇总 】")
        print(f"最大 RTT: {df.max():.2f} ms")
        print(f"最小 RTT: {df.min():.2f} ms")
        print(f"平均 RTT: {df.mean():.2f} ms")
        print(f"RTT 标准差: {df.std():.2f} ms")
        loss_rate = ((total_sent_count - 30) / total_sent_count) * 100
        print(f"实际总发包数: {total_sent_count}")
        print(f"丢包率: {loss_rate:.2f}%")



if __name__ == '__main__':
    main()