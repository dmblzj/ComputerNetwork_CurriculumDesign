# TCP Socket Programming

## 1. 项目简介

本系统实现了一个基于 TCP 的自定义应用层协议，用于实现客户端与服务器之间的数据分块传输与反转功能。客户端将文件按随机长度分块后发送至服务器，服务器对每个数据块进行反转并返回，最终由客户端拼接还原。

## 2. 运行环境

- **开发语言**: Python 3.x
- **依赖库**: 本项目仅使用 Python 标准库 (socket, struct, argparse, random, logging, threading)，无需安装额外第三方库。

## 3. 文件说明

- tcp_server.py: 服务器端程序，支持多线程并发处理，负责接收请求、反转数据块。
- tcp_client.py: 客户端程序，负责文件读取、随机分块、发送请求及最终结果拼接。
- test.txt: 测试用源文件。
- server_log.txt: 服务器运行日志。
- client_log.txt: 客户端运行日志。
- tcp_packet_capture.doc: 协议抓包分析文档。

## 4. 运行方法

### 步骤一：启动服务器

在终端（或服务器端环境）执行以下命令：

codeBash

```
python tcp_server.py <Port>
```

*示例*: python tcp_server.py 8888

### 步骤二：运行客户端

在另一个终端（或客户端环境）执行以下命令：

codeBash

```
python tcp_client.py <Server_IP> <Port> <File_Path> <Lmin> <Lmax> <Seed>
```

*示例*: python tcp_client.py 127.0.0.1 8888 test.txt 5 15 42

- Server_IP: 服务器地址。
- Port: 服务器端口。
- File_Path: 待发送的文件路径。
- Lmin / Lmax: 随机分块的长度范围。
- Seed: 随机种子，用于复现分块逻辑。

## 5. 功能特点

- **协议定制**: 自定义四种报文类型 (Type 1-4)，采用大端序字节流传输，有效避免粘包问题。
- **随机分块**: 支持在客户端根据指定参数进行随机切片，验收时可通过 seed 复现。
- **并发处理**: 基于多线程模型，服务器可同时处理多个客户端的连接请求。
- **日志记录**: 程序自动生成详细的操作日志，记录报文发送与接收的时间、内容及处理状态。