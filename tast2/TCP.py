import struct
# 常量
FLAG_SYN = 0x01
FLAG_ACK = 0x02
FLAG_DATA = 0x08

class TCP:
    HEADER_FORMAT = '!IIBHHB'
    HEADER_LENGTH = 14

    def __init__(self,seq=0, ack=0, flags=0, student_id=0, length=0, data=b''):
        #seq(4)+ack(4)+flags(1)+student_id(2)+长度(2)+保留(1)=14字节
        self.seq = seq #4
        self.ack = ack #4
        self.flags = flags #1
        self.student_id = student_id #2
        self.data = data
        self.length = len(data) #2


    def tcp_encode(self):
        header=struct.pack(self.HEADER_FORMAT,self.seq,self.ack,self.flags,self.student_id,self.length,0)
        return header+self.data


    @classmethod
    def tcp_decode(cls,raw_bytes):
        if len(raw_bytes)<cls.HEADER_LENGTH:
            return None

        header=raw_bytes[:cls.HEADER_LENGTH]
        data=raw_bytes[cls.HEADER_LENGTH:]

        unpacked=struct.unpack(cls.HEADER_FORMAT,header)

        packet = TCP(
            seq=unpacked[0],
            ack=unpacked[1],
            flags=unpacked[2],
            student_id=unpacked[3],
            length=unpacked[4],
            data=data
        )
        return packet
