qdd

## 启动
* 拷贝config.yaml.example为config.yaml
* 修改config.yaml
  - 修改公众号配置
  - 修改OpenAI配置
  - 修改UNSPLASH_KEY
* 安装依赖
  - Linux
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  ```
  - Windows
  ```bash
  python3 -m venv .venv
  .\venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  ```
4.安装playwright
```bash
playwright install
```
5.开始搞钱
```bash
python3 qdd.py
```
6.业务交流

<img src="./res/wegroup.jpg" width="300" alt="微信">