# Kindle Dashboard（纯 Python 版）

给 Kindle 提供仪表盘图片的小服务。用 FastAPI 直接生成 PNG，不需要 Docker，也不需要 Glances。

显示内容：

- **系统指标**：CPU、内存、温度、负载、Swap、开机时长、磁盘（由 `psutil` 直接读取）
- **股票**：你配置的股票代码，显示价格和涨跌（`yfinance`，有缓存）
- **天气**：Open-Meteo，无需 API Key，可选开启

## 安装

```sh
python -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env              # Windows: Copy-Item .env.example .env
```

编辑 `.env`，至少设置 `DISPLAY_TZ`，需要天气时设置 `WEATHER_ENABLED=true` 和经纬度，需要股票时设置 `STOCK_SYMBOLS`。

## 启动

```sh
uvicorn app:app --host 0.0.0.0 --port 8070
```

打开 `http://<服务器IP>:8070/preview` 查看竖屏效果，`/preview/landscape` 查看横屏效果。

## 接口

| 路径 | 说明 |
| --- | --- |
| `/dash.png` | 600×800 竖屏 PNG（老款 Kindle 默认） |
| `/dash-landscape.png` | 800×600 横屏 PNG（浏览器预览用） |
| `/dash-landscape-kindle.png` | 横屏内容旋转成 600×800，供 Kindle 横屏使用 |
| `/time` | 服务器当前 Unix 时间，Kindle 用它对齐分钟刷新 |
| `/healthz` | 健康检查 |

## 配置项

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DASHBOARD_TITLE` | `HOMELAB` | 标题 |
| `DISPLAY_TZ` | `UTC` | 显示时区（IANA 名称） |
| `DISK1_LABEL` / `DISK1_MOUNT` | `SYSTEM` / `/`（Windows 为 `C:\`） | 第一块磁盘 |
| `DISK2_LABEL` / `DISK2_MOUNT` | `DATA` / 空 | 第二块磁盘，留空则不显示 |
| `WEATHER_ENABLED` | `false` | 是否开启天气 |
| `WEATHER_LAT` / `WEATHER_LON` | `0` / `0` | 天气坐标 |
| `WEATHER_TEMP_UNIT` / `WEATHER_WIND_UNIT` | `fahrenheit` / `mph` | 单位 |
| `STOCK_SYMBOLS` | `QQQ,SPY,NVDA` | 股票代码，逗号分隔，最多显示 9 个 |
| `STOCK_CACHE_SECONDS` | `300` | 股票缓存时间 |
| `RENDER_CACHE_SECONDS` | `2` | 短时间内重复请求复用同一张图 |

## 注意事项

- 股票行情来自 Yahoo Finance，属于延迟数据，仅供参考。
- CPU 温度和负载只有 Linux 能读到；在 Windows/macOS 上显示 `--`。
- 服务没有鉴权，只在可信局域网内使用，不要暴露到公网。

## 作为服务长期运行（Linux，systemd）

`/etc/systemd/system/kindle-dashboard.service`：

```ini
[Unit]
Description=Kindle Dashboard
After=network-online.target

[Service]
WorkingDirectory=/home/<用户名>/kindle-dashboard
ExecStart=/home/<用户名>/kindle-dashboard/.venv/bin/uvicorn app:app --host 0.0.0.0 --port 8070
Restart=on-failure
User=<用户名>

[Install]
WantedBy=multi-user.target
```

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now kindle-dashboard
```

## Kindle 端

`kindle-extension/` 与之前相同，未做修改。在 `config.sh` 中把 `DASHBOARD_BASE_URL` 设为服务器地址（不带路径）即可。

## 测试

```sh
python -m unittest discover -s tests -v
```

测试完全离线运行，不依赖网络、Glances 或 Docker。
