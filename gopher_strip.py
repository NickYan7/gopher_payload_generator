#! /usr/bin/env python
# 生成 gopher payload
# 适用于 http 访问
import os, argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-f',
        '--filename',
        type=str,
        dest='filename',
        help="type the filename you want to generate..."
    )
    args = parser.parse_args()
    if args.filename:
        return args.filename
    if args.filename == None:
        parser.print_help()
        os._exit(0)

def convert(filename):
    payload = ''
    with open(filename, 'r') as f:
        for line in f.readlines():
            if line[-3:-1] == r"\r" or line[-1:-3:-1] == "r\\":
                line = line.replace(r'\r', '%0d%0a').strip()
                payload = payload + line
            elif line == '\n':
                payload = payload + '%0a'
            else:
                line = line.strip()
                payload = payload + line

    return payload


if __name__ == "__main__":
    result = main()
    print(convert(result))