#! /usr/bin/env python
# -*- coding: utf-8 -*-
# 生成 gopher payload
# 将16进制流或者post数据文件,redis数据文件转化为gopher协议可以发送的形式.
# 适用于 curl
import optparse

def hexs2url(hexstr):
    i = 0
    while True:
        if i % 3 == 0:
            hexstr = hexstr[:i] + '%' + hexstr[i:]
        i += 1
        if i == len(hexstr):
            break
    print(hexstr)

def getfiletourl(path):
    with open(path, 'r') as f:
        content = f.read()
    hexstr = ''
    for i in content:
        s = hex(ord(i)).replace('0x', '%')
        if len(s)<3:
            s = s[:1] + '0' + s[1:]
        if s == '%0a':
            s = '%0d%0a'
        hexstr += s
    print(hexstr)

def main():
    parse = optparse.OptionParser("usage%prog --hex <target stream> -r <target file path>")
    parse.add_option('--hex', dest='hex', type='string', help='specify target stream')
    parse.add_option('-r', dest='path', type='string', help='specify target file path')
    (options, args) = parse.parse_args()
    if options.hex:
        hexs2url(options.hex)
    if options.path:
        getfiletourl(options.path)

if __name__=='__main__':
    main()