# Keybox Checker
[![actions](https://github.com/KimmyXYC/KeyboxChecker/actions/workflows/docker-ci.yaml/badge.svg)](https://github.com/KimmyXYC/KeyboxChecker/actions/workflows/docker-ci.yaml)
## 部署 / Deployment

- 下载源码。Download the code.
```shell
git clone https://github.com/KimmyXYC/KeyboxChecker.git
cd KeyboxChecker
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

### 本地部署 / Local Deployment
- 安装依赖并运行。Install dependencies and run.
```shell
pip3 install -r requirements.txt
python3 main.py
```

### Docker 部署 / Docker Deployment
- 使用预构建镜像。Use pre-built image.
```shell
docker run -d --name keyboxchecker -v $(pwd)/Config:/app/Config ghcr.io/kimmyxyc/keyboxchecker:main
```

## 使用 / Usage
私聊发送 keybox.xml 文件 或 对 keybox.xml 文件回复 /check  
Send the keybox.xml file in the private chat or reply with /check to keybox.xml file.

![Usage](./screenshot.png)
