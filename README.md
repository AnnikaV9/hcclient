# hcclient
A terminal client for connecting to [hack.chat](https://github.com/hack-chat/main) servers.



## Setup & Usage

```
git clone https://github.com/AnnikaV9/hcclient.git
cd hcclient
pip3 install -r requirements.txt
python3 hcclient --help
```


## Docker image
From Docker Hub:
```
docker pull annikav9/hcclient
docker run --rm -it annikav9/hcclient --help
```
Building locally:
```
git clone https://github.com/AnnikaV9/hcclient.git
cd hcclient
docker build -t hcclient .
docker run --rm -it hcclient --help
```



## Todo
- Add color schemes
- Add mod/admin commands that can enabled with flags (eg. `--is-mod`)
