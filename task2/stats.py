import time
import statistics


class RTTStats:
    def __init__(self):
        self.rtts = []
        self.send_times = {}

    def record_send(self, seq):
        self.send_times[seq] = time.time()

    def record_ack(self, seq):
        if seq in self.send_times:
            rtt = (time.time() - self.send_times[seq]) * 1000
            self.rtts.append(rtt)
            del self.send_times[seq]
            return rtt
        return None

    def get_stats(self):
        if not self.rtts:
            return None
        return {
            'min': min(self.rtts),
            'max': max(self.rtts),
            'mean': statistics.mean(self.rtts),
            'stdev': statistics.stdev(self.rtts) if len(self.rtts) > 1 else 0,
            'count': len(self.rtts)
        }

    def print_stats(self):
        s = self.get_stats()
        if not s:
            print("无 RTT 数据")
            return
        print(f"\nRTT 统计: 样本={s['count']}, 最小={s['min']:.2f}ms, "
              f"最大={s['max']:.2f}ms, 平均={s['mean']:.2f}ms, 标准差={s['stdev']:.2f}ms")


class LossStats:
    def __init__(self):
        self.total_sent = 0
        self.unique_sent = 0

    def record_send(self, is_new_packet):
        self.total_sent += 1
        if is_new_packet:
            self.unique_sent += 1

    def get_loss_rate(self):
        if self.total_sent == 0:
            return 0
        return 1 - (self.unique_sent / self.total_sent)