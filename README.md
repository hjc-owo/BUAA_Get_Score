# BUAA_Score

## 使用说明

使用前先根据你的情况修改部分代码，修改好后保存，然后在本文件夹终端输入

```bash
python main.py
```

就进入运行状态了。

## 需要修改的部分

可以选择需要手动输入或者直接写进代码。

### 邮箱配置

具体表现为：

```python
# 9 - 12 行
MAIL_HOST = "smtp.qq.com"  # 设置SMTP服务器，如smtp.qq.com smtp.163.com
MAIL_USER = "******@qq.com"  # 发送邮箱的用户名，如xxxxxx@qq.com xxx@163.com
MAIL_PASS = "**********"  # 发送邮箱的密码（注：QQ邮箱需要开启SMTP服务后在此填写授权码）
RECEIVER = "******@qq.com"  # 收件邮箱，格式同发件邮箱
```

和

```python
# 14 - 17 行
MAIL_HOST = input("请输入SMTP服务器，如smtp.qq.com smtp.163.com:")
MAIL_USER = input("请输入发送邮箱的用户名，如****@qq.com:")
MAIL_PASS = input("请输入发送邮箱的密码（注：QQ邮箱需要开启SMTP服务后在此填写授权码）:")
RECEIVER = input("请输入收件邮箱，格式同发件邮箱:")
```

两者选一个注释掉，注释上面的表示手动输入；

注释下面的表示直接在代码进行配置，那就意味着首先需要选择用于发送成绩信息的邮箱

需要在邮箱提供商处设置开启SMTP，

并将SMTP服务器、发件邮箱用户名、发件邮箱密码、收件邮箱用户名依次替换上面的内容行的对应内容。

*其中发件邮箱和收件邮箱可以相同。*

### 北航统一认证

同样的，在

```python
# 59 行
ndata = {'username': "********", 'password': "********", }  # 请填写自己的学号和密码
```

和

```python
# 18、19 行
username = input("请输入学号:")
password = input("请输入密码:")
# 58 行
ndata = {'username': username, 'password': password}
```

两者选一个注释掉。

同样的，如果注释下面的选择上面的，就需要设置你的北航账号密码

修改`get_sess()`函数的对应内容即可。

```python
ndata = {'username': "********", 'password': "********", }  # 请填写自己的学号和密码
```

### 设置需要查询的学期

两种方式最后都需要设置需要查询的学期 

修改文件靠末尾`get_score_list()`函数的参数即可。

```python
get_score_list('2022-2023', '1')  # 在这里改你要查询的学期 1 2 3分别代表秋 春 夏季学期
```

## 注意事项

要保持本脚本可以正常运行，需要保持网络正常、脚本窗口不关闭。

如果想停止接收邮件，关闭该窗口即可。

如果提示`ERROR：无法发送邮件`，请检查你的邮箱账号密码是否正确。

## 部署到服务器（可选）

如果有自己的服务器，可以在服务器上运行。

但是命令和当前的终端窗口是绑定在一起的，换句话说，如果关闭了本地的终端窗口，运行就会被打断，那么有没有一个简单的方法，直接放在服务器呢？

可以尝试使用`tmux`，可以把当前的命令和打开的终端窗口取消绑定，换句话说，即使关掉了本地的终端窗口，命令仍然可以继续运行。

### tmux 的安装

```bash
sudo apt install tmux
```

### 创建新的窗口

创建一个新的名字叫做 score 的窗口

```bash
tmux new -s score
```

### 进入窗口

进入名字叫做 score 的窗口

```bash
tmux attach-session -t score
```

### 删除窗口

删除名字叫做 score 的窗口

```bash
tmux kill-session -t score
```

### 查看窗口列表

```bash
tmux ls
```