# hcclient
A terminal client for connecting to [hack.chat](https://github.com/hack-chat/main) servers.


## Setup & Usage
Without Docker
```
git clone https://github.com/AnnikaV9/hcclient.git
cd hcclient
pip3 install -r requirements.txt
python3 hcclient --help
```
With Docker
```
git clone https://github.com/AnnikaV9/hcclient.git
cd hcclient
docker build -t hcclient .
docker run --rm -it hcclient --help
```
