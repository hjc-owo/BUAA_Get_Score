import json
import smtplib
import time
from email.header import Header
from email.mime.text import MIMEText

import requests

# 两种方式配置邮箱信息
# 1.直接在这里填写
# MAIL_HOST = "smtp.qq.com"  # 设置SMTP服务器，如smtp.qq.com smtp.163.com
# MAIL_USER = "******@qq.com"  # 发送邮箱的用户名，如xxxxxx@qq.com xxx@163.com
# MAIL_PASS = "**********"  # 发送邮箱的密码（注：QQ邮箱需要开启SMTP服务后在此填写授权码）
# RECEIVER = "******@qq.com"  # 收件邮箱，格式同发件邮箱

# 2.运行时输入
MAIL_HOST = input("请输入SMTP服务器，如smtp.qq.com smtp.163.com:")
MAIL_USER = input("请输入发送邮箱的用户名，如****@qq.com:")
MAIL_PASS = input("请输入发送邮箱的密码（注：QQ邮箱需要开启SMTP服务后在此填写授权码）:")
RECEIVER = input("请输入收件邮箱，格式同发件邮箱:")

# 两种方式配置学号密码
# 1.直接在这里填写
# ndata = {'username': "********", 'password': "********", }  # 请填写自己的学号和密码

# 2.运行时输入
username = input("请输入学号:")
password = input("请输入密码:")
ndata = {'username': username, 'password': password}

# 请填写想要查询的学年和学期
year = '2022-2023'  # 学年
term = '2'  # 1 2 3分别代表秋 春 夏季学期

# 下面的代码不需要修改
cookies = {'eai-sess': '', }
headers = {
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'zh,en-US;q=0.9,en;q=0.8,zh-CN;q=0.7',
    'Connection': 'keep-alive',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'DNT': '1',
    'Origin': 'https://app.buaa.edu.cn',
    'Referer': 'https://app.buaa.edu.cn/buaascore/wap/default/index',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest',
    'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="102", "Google Chrome";v="102"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}
base = []


def get_sess():
    headerss = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh,en-US;q=0.9,en;q=0.8,zh-CN;q=0.7',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'DNT': '1',
        'Origin': 'https://app.buaa.edu.cn',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="102", "Google Chrome";v="102"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    }
    try:
        response = requests.post('https://app.buaa.edu.cn/uc/wap/login/check', headers=headerss, data=ndata)
        resp = json.loads(response.text)
        if resp['e'] == 0 and resp['m'] == '操作成功':
            sess = response.cookies.get("eai-sess")
        else:
            sess = "error"
    except:
        sess = "error"
    return sess


def get_score_list(year, xq):  # year 格式为 2020-2021 字符串  xq取值为1 2 3 字符串
    data = {'xq': xq, 'year': year}
    try:
        response = requests.post('https://app.buaa.edu.cn/buaascore/wap/default/index',
                                 cookies=cookies,
                                 headers=headers,
                                 data=data)
        print("请求时间{}".format(time.ctime()))
    except:
        return "error"
    dic = json.loads(response.text)
    res = []
    for i in dic['d'].values():
        res.append({'km': i['kcmc'], 'cj': i['kccj'], 'xf': i['xf']})
    return res


def send_mail(title, content):
    # 第三方 SMTP 服务
    print("准备发送邮件")
    mail_host = MAIL_HOST
    mail_user = MAIL_USER
    mail_pass = MAIL_PASS
    sender = mail_user
    receivers = RECEIVER
    message = MIMEText(content, 'plain', 'utf-8')
    message['From'] = Header(sender)  # 发件人
    message['To'] = Header(receivers, 'utf-8')  # 收件人
    subject = title  # 主题
    message['Subject'] = Header(subject, 'utf-8')
    print('Prepare success')
    try:
        smtpObj = smtplib.SMTP()
        smtpObj.connect(mail_host, 25)  # 25 为 SMTP 端口号
        print('Connect success')
        smtpObj.login(mail_user, mail_pass)
        print('Login success')
        smtpObj.sendmail(sender, receivers, str(message))
        print("邮件发送成功")
    except smtplib.SMTPException:
        print("ERROR：无法发送邮件")


def to_content(lis):
    msg = "本学期的课程成绩如下:\n"
    tplt = "{0:{3}^10}\t{1:{3}^10}\t{2:^10}\n"
    msg += tplt.format("课程", "成绩", "学分", chr(12288))
    for i in lis:
        msg += tplt.format(i['km'], i['cj'], i['xf'], chr(12288))
    return msg


succeed = False
right_username = ""
right_password = ""
while True:
    while True:
        cookies['eai-sess'] = get_sess()
        if cookies['eai-sess'] == 'error':
            print("登录失败，请重新输入账号密码!!!")
            username = right_username if succeed else input("请输入学号:")
            password = right_password if succeed else input("请输入密码:")
        else:
            print("登录成功")
            succeed = True
            right_username = username
            right_password = password
            break
    raw = get_score_list(year, term)
    if raw == "error":
        time.sleep(60)
        continue
    tmp = [i for i in raw if i['cj'] is not None]
    if len(tmp) > len(base):
        newobjs = [i['km'] for i in tmp if i not in base]
        send_mail("新出了{}门：{}".format(len(newobjs), "，".join(newobjs)), to_content(tmp))
        base = tmp
    time.sleep(60)
