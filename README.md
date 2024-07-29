# Keybox Checker
## 部署 / Deployment

- 下载源码。Download the code.
```shell
git clone https://github.com/KimmyXYC/KeyboxChecker.git
cd ApproveByPoll
```

- 复制配置文件。Copy configuration file.
```shell
cp Config/app_exp.toml Config/app.toml
```

- 填写配置文件。Fill out the configuration file.
```toml
[bot]
master = [100, 200]
botToken = 'key' # Required, Bot Token


[proxy]
status = false
url = "socks5://127.0.0.1:7890"
```

- 安装依赖并运行。Install dependencies and run.
```shell
pip3 install -r requirements.txt
python3 main.py
```

## 使用 / Usage
Send the keybox.xml file in the private message or reply with /check to keybox.xml.

![Usage](./screenshot.png)
