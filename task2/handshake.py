import socket
import random
import protocol as proto


def client_handshake(server_ip, server_port, local_port, timeout=1.0, max_retries=3):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)

    client_seq = random.randint(0, 10000)

    syn_packet = proto.make_packet(
        src_ip='0.0.0.0', dst_ip=server_ip,
        src_port=local_port, dst_port=server_port,
        seq=client_seq, ack=0, flags=proto.FLAG_SYN,
        student_id=proto.STUDENT_ID, data=b''
    )

    for retry in range(max_retries):
        print(f"[握手] 发送 SYN, seq={client_seq}")
        sock.sendto(syn_packet, (server_ip, server_port))

        try:
            data, addr = sock.recvfrom(1024)
            result = proto.parse_packet(server_ip, '0.0.0.0', data)
            if result:
                _, _, seq, ack, flags, _, _ = result
                if flags == (proto.FLAG_SYN | proto.FLAG_ACK) and ack == client_seq + 1:
                    server_seq = seq
                    ack_packet = proto.make_packet(
                        src_ip='0.0.0.0', dst_ip=server_ip,
                        src_port=local_port, dst_port=server_port,
                        seq=client_seq + 1, ack=server_seq + 1,
                        flags=proto.FLAG_ACK, student_id=0, data=b''
                    )
                    sock.sendto(ack_packet, (server_ip, server_port))
                    print("[握手] 成功")
                    return sock, client_seq, server_seq, True
        except socket.timeout:
            print("[握手] 超时重试")
            continue

    sock.close()
    return None, 0, 0, False


def server_handshake(sock, expected_student_id, timeout=2.0):
    while True:
        data, addr = sock.recvfrom(1024)
        server_ip = sock.getsockname()[0]
        client_ip = addr[0]
        result = proto.parse_packet(client_ip, server_ip, data)
        if not result:
            continue
        _, _, seq, ack, flags, student_id, _ = result
        if flags == proto.FLAG_SYN and student_id == expected_student_id:
            client_seq = seq
            server_seq = random.randint(0, 10000)
            syn_ack = proto.make_packet(
                src_ip=server_ip, dst_ip=client_ip,
                src_port=addr[1], dst_port=addr[1],
                seq=server_seq, ack=client_seq + 1,
                flags=proto.FLAG_SYN | proto.FLAG_ACK,
                student_id=0, data=b''
            )
            sock.sendto(syn_ack, addr)
            sock.settimeout(timeout)
            try:
                data2, _ = sock.recvfrom(1024)
                result2 = proto.parse_packet(client_ip, server_ip, data2)
                if result2 and result2[4] == proto.FLAG_ACK:
                    sock.settimeout(None)
                    return addr, client_seq, server_seq
            except socket.timeout:
                sock.settimeout(None)
                return addr, client_seq, server_seq