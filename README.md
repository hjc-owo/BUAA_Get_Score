# BUAA_Score 🚀

## 使用说明 📖

由于北航将login API的`POST`方法禁用，我们采取了`selenium`库模拟点击登录的方式。✨

在使用前，请根据你的需求修改`config.yaml`文件，内容包括邮箱配置、北航统一认证的学号密码、以及你想要查询的学年学期。修改完后保存文件，然后在本文件夹终端输入以下命令，启动程序：

```bash
python main.py
```

这样，程序就会开始运行啦！🎉

## 邮箱配置说明 📧

`config.yaml`文件中的`email.enabled`设置为`True`，即可在邮件配置正确的情况下，开启邮箱服务。

1. 需要在邮箱提供商处设置开启SMTP；
2. 修改`config.yaml`文件中相应的SMTP服务器、发件邮箱用户名、发件邮箱密码、收件邮箱用户名。

*发件邮箱和收件邮箱可以是相同的哦！*

## 注意事项 ⚠️

**目前只能查看默认的学年学期的成绩，暂不支持修改学期。**

请确保网络连接正常，且脚本窗口未关闭，以保证脚本能够正常运行。

如果想停止接收邮件，只需关闭窗口即可。❌

如果提示 `ERROR：无法发送邮件`，请检查你的邮箱账号密码是否正确。🔍

## 部署到服务器（可选） 🌐

如果你有自己的服务器，可以将脚本部署到服务器上运行。

但是需要注意，命令和当前终端窗口是绑定在一起的。如果关闭了本地终端窗口，运行会被打断。那么，有没有一个简单的方式让命令继续运行呢？🤔

可以使用`tmux`，它允许你将当前命令和终端窗口解绑，即使关闭本地终端，命令依然会继续执行。💡

### tmux 的安装 🛠️

```bash
sudo apt install tmux
```

### 创建新的窗口 🪟

创建一个新的名字叫做 score 的窗口

```bash
tmux new -s score
```

### 进入窗口 🧑‍💻

进入名字叫做 score 的窗口

```bash
tmux a -t score
```

### 删除窗口 ❌

删除名字叫做 score 的窗口

```bash
tmux kill-session -t score
```

### 查看窗口列表 📋

```bash
tmux ls
```