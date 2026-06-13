import socket
import struct

FLAG_SYN  = 0x01
FLAG_ACK  = 0x02
FLAG_FIN  = 0x04
FLAG_DATA = 0x08

STUDENT_ID_LAST4 = 2704
STUDENT_ID = STUDENT_ID_LAST4 ^ 0x5A3C

def calculate_checksum(data):
    total = 0
    for i in range(0, len(data), 2):
        word = (data[i] << 8) + (data[i+1] if i+1 < len(data) else 0)
        total += word
        while total > 0xFFFF:
            total = (total & 0xFFFF) + (total >> 16)
    return (~total) & 0xFFFF

def calculate_checksum_with_pseudo(src_ip, dst_ip, udp_packet):
    src_bytes = socket.inet_aton(src_ip)
    dst_bytes = socket.inet_aton(dst_ip)
    protocol = 17
    udp_length = len(udp_packet)
    pseudo_header = struct.pack('!4s4sBBH', src_bytes, dst_bytes, 0, protocol, udp_length)
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
    data = packet[20:20+length]
    return (src_port, dst_port, seq, ack, flags, student_id, data)