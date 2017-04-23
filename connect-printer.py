#!/usr/bin/python3
import socket, subprocess, snmp_msg

PRINTER_PORT=54921
LOCAL_PORT=54925

bcast_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
bcast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
bcast_sock.connect(('255.255.255.255', 161))

local_host = socket.gethostname()
local_addr = bcast_sock.getsockname()
local_ip = local_addr[0]
local_port = local_addr[1]
print('this hostname:', local_host, '=', local_ip)

msg = snmp_msg.create()
bcast_sock.send(msg)

bcast_sock.close()
read_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
read_sock.bind(local_addr)
msg, remote_addr = read_sock.recvfrom(2048)
print('got response from', remote_addr, '!')
snmp_msg.print_msg(msg)

printer_addr = remote_addr[0]

common_args = ['-v', '1', '-c', 'internal', printer_addr]

# 1.3.6.1.4.1.2435 = brother MIB
# see http://www.oidview.com/mibs/2435/BROTHER-MIB.html

# brother/nm/system/net-peripheral/net-printer/generalDeviceStatus/brieee1284id
# 1.3.6.1.4.1.2435.2.3.9.1.1.7.0

# sysName
# 1.3.6.1.2.1.1.5.0

# ifPhysAddress
# 1.3.6.1.2.1.2.2.1.6.1

# brother/nm/interface/npCard/brnetConfig/brconfig/brpsHardwareType
# 1.3.6.1.4.1.2435.2.4.3.1240.1.3.0

# sysDescr
# 1.3.6.1.2.1.1.1.0

# sysLocation
# 1.3.6.1.2.1.1.6.0

# private entreprise
# 1.3.6.1.4.1.1240.2.3.4.5.2.6.0

# see http://www.oidview.com/mibs/2435/BROTHER-MIB.html

# 1 (iso). 3 (org). 6 (dod). 1 (internet). 2 (mgmt). 1 (mib-2).
# 43 (printmib).
# 5 (prtGeneral). 1 (prtGeneralTable).
# 1 (prtGeneralEntry). 2 (prtGeneralCurrentLocalization) .1
subprocess.run(['snmpget'] + common_args + ['1.3.6.1.2.1.43.5.1.1.2.1'])

# 7 (prtLocalization). 1 (prtLocalizationTable).
# 1 (prtLocalizationEntry). 4 (prtLocalizationCharacterSet)
# .1.2
subprocess.run(['snmpget'] + common_args + ['1.3.6.1.2.1.43.7.1.1.4.1.2'])

# 1.3.6.1.4.1.2435 (brother)
# .2 (nm)
# .3 (system)
# .9 (net-peripheral)
# .2 (net-MFP)
# .11 (scanner-setup)
# .1 (scanToInfo)
# .1 (brRegisterKeyInfo)
# .0
args = ['snmpset'] + common_args

funcs = {1: 'IMAGE', 2: 'EMAIL', 3: 'OCR', 5: 'FILE'}
for num, func in funcs.items():
  # '1.3.6.1.4.1.2435.2.3.9.2.11.1.1.0'
  args += ['1.3.6.1.4.1.2435.2.3.9.2.11.1.1.0', 's',
    'TYPE=BR;BUTTON=SCAN;USER="' + local_host + '";FUNC=' + str(func) + ';' +
    'HOST=' + local_ip + ':' + str(LOCAL_PORT) + ';APPNUM=' + str(num) + ';DURATION=360;CC=1;'
  ]

subprocess.run(args)

# Set up a UDP server
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Start listening
listen_addr = (local_ip, LOCAL_PORT)
udp_sock.bind(listen_addr)

# Wait for initial message and reply with it
data, addr = udp_sock.recvfrom(1024)
udp_sock.sendto(data, addr)

# now connect to the printer
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((printer_addr, PRINTER_PORT))

data = sock.recv(9)
print(data)
assert data == b'+OK 200\r\n'

def send_command(socket, command):
  sock.sendall(b'\x1b' + command + b'\n\x80')

# K for OK?
send_command(sock, b'K')
data = sock.recv(32)
print(data)

# I for information?
send_command(sock, b'''I
R=300,300
M=CGRAY
D=SIN''')
data = sock.recv(32)
print(data)

# b'\x00\x1d\x00300,300,2,209,2480,291,3437,\x00'
# response: res width, res height, 2 = ??,
# 209 = width, 2480 = max scanner width, 291 = height, 3437 = max scanner height
# units of max scanner are in dots (depends on resolution)

# X for eXecute?
# R = resolution
# M = CGRAY ?
# C = always JPEG
# J = always MIN
# B = Brightness (0 to 100)
# N = contrast (0 to 100)
# A = area to scan (depends on resolution)
# E = ?
# G = remove background?
# (if G, then L = level between 128 and 192?)
send_command(sock, b'''X
R=300,300
M=CGRAY
C=JPEG
J=MIN
B=50
N=50
A=0,0,2416,3437
D=SIN
E=0
G=0''')

with open('image.jpg', 'wb') as f:
  while True:
    data = sock.recv(10)
    print(data)
    # b'd\x07\x00\x01\x00\x84\x10\x01\x00\x00'
    # response: after \x84 we have width (2 bytes, little endian) and (presumably) height (2 bytes, little endian)
    data = sock.recv(2)
    block_len = int.from_bytes(data, byteorder='little')
    print('reading', str(block_len), 'from socket')

    remain = block_len
    while remain > 0:
      data = sock.recv(remain)
      remain -= len(data)
      f.write(data)

print('done')
