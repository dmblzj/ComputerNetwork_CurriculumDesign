# Task 2: UDP Socket Programming - GBN Protocol Implementation

## 1. 项目简介

本程序基于 UDP 协议实现了一个应用层可靠传输协议，模拟了 **GBN (Go-Back-N, 回退 N 帧)** 协议。通过自定义应用层报文格式，实现了连接建立（三次握手）、数据传输、超时重传、流量控制及丢包统计等功能。

## 2. 运行环境

- **语言**: Python 3.x
- **依赖库**:
  - pandas (用于 RTT 数据统计)
  - argparse, socket, threading, logging (内置库)
- **平台**: 支持 Windows/Linux 命令行环境

## 3. 安装依赖

请在终端执行以下命令安装必要的数据分析库：

codeBash

```
pip install pandas
```

## 4. 运行方法

### 步骤 1：启动服务端

服务端需指定监听端口及模拟丢包率（0~1 之间，如 0.2 代表 20% 丢包率）。

codeBash

```
python udpserver.py <port> <loss_rate>
# 示例：python udpserver.py 7777 0.2
```

### 步骤 2：启动客户端

客户端连接服务端，需指定服务器 IP 和端口。

codeBash

```
python udpclient.py <server_ip> <server_port>
# 示例：python udpclient.py 127.0.0.1 7777
```

## 5. 实现功能亮点

- **三次握手**: 在 UDP 之上通过自定义报文头实现了 SYN、SYN+ACK、ACK 的连接建立，并包含基于 XOR 规则的 StudentID 校验。
- **可靠传输机制**:
  - **GBN 协议**: 实现了发送窗口管理，支持顺序发送与累积确认。
  - **超时重传**: 采用 time_lit 超时判定，发生丢包时自动触发从 base 开始的全部数据包重传。
- **实时统计**:
  - 程序运行过程中实时生成 udpclient.txt 日志，详细记录发包、收包及重传时间戳。
  - 传输结束后利用 pandas 自动统计最大/最小/平均 RTT 及标准差，并计算传输丢包率。
- **交互友好**: 支持通过命令行参数灵活配置网络参数，无需硬编码。

## 6. 注意事项

- **日志验证**: 运行结束后产生的日志文件 (udpclient.txt) 与 Wireshark 抓包数据时间戳吻合，可用于验证丢包重传逻辑。
- **丢包率统计**: 丢包率计算公式采用 (总发送尝试次数 - 初始包数) / 总发送尝试次数，反映了重传带来的网络代价。