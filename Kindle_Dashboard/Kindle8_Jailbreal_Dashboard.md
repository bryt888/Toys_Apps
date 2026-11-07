# Kindle 8th Gen Jailbreak & Dashboard 安装总结

这次我们成功把一台闲置多年的 Amazon Kindle 第八代改造成了 电子墨水天气及系统监控 Dashboard。

整个过程包括：恢复出厂设置、WinterBreak2 越狱、安装 KUAL、安装 Dashboard 插件，以及在 Ubuntu 24.04 上部署服务器。

下面记录实际成功的操作流程，方便以后重新安装或改造其他 Kindle。

## 一、设备及最终环境

| 项目        | 配置                          |
| --------- | --------------------------- |
| Kindle 型号 | Kindle Basic 8th Generation |
| 设备代号      | KT3                         |
| 硬件型号      | SY69JL                      |
| 固件        | 5.16.2.1.1                  |
| 屏幕        | 6 英寸 E-Ink，16 级灰度           |
| 竖屏分辨率     | 600 × 800                   |
| 横屏分辨率     | 800 × 600                   |
| 越狱工具      | WinterBreak2                |
| 越狱版本      | jb.sh v2.6.0                |
| 启动器       | KUAL / PEKI                 |
| Dashboard | kindle-homelab-dashboard    |
| 服务器       | Intel Mac Mini，Ubuntu 24.04 |
| 服务端口      | 8070                        |
| 系统监控      | Glances 4.5.9               |

最终架构：

```
Mac Mini (Ubuntu 24.04)
    |
    |-- Dashboard Server
    |      |-- 天气数据
    |      |-- 系统监控数据
    |      |-- PNG 图片生成
    |      |
    |      +-- HTTP :8070
    |
    |-- Glances
    |      +-- HTTP :61208
    |
    +--------- 家庭 Wi-Fi --------+
                                 |
                          Kindle KT3
                                 |
                          WinterBreak2
                                 |
                               KUAL
                                 |
                        Homelab Dashboard
                                 |
                         E-Ink 全屏显示
```

## 二、Kindle 越狱

### Step 1：检查设备与固件

在 Kindle 上进入：

`Settings → Device Options → Device Info`

确认：

```
Kindle (8th Generation)
Firmware: 5.16.2.1.1
```

重要：不要先升级 Kindle 固件。 越狱工具的兼容性与固件版本直接相关。

### Step 2：恢复出厂设置（仅在需要时）

我们的 Kindle 原来启用了 Parental Controls，但忘记了 PIN，因此无法访问 Kindle Store。

使用了 Amazon 的重置代码：

```
111222777
```

在家长控制 PIN 输入框输入后，执行 Factory Reset。

注意：

- 这不是普通解锁密码，而是触发恢复出厂设置。
- 会清除本地文件和设置。
- 通常不会降级或升级固件。

恢复后选择语言和国家，在 Wi-Fi 设置页面点击 Set up later。

设备可以保持 `Unregistered` 状态，不必注册 Amazon 账户。

如果 Kindle 没有家长控制问题，这一步可以跳过。

### Step 3：选择 WinterBreak2

我们最初尝试了 WinterBreak，但由于 Kindle 没有注册 Amazon 账户，通过 Kindle Store 启动时始终进入 Wi-Fi 选择页面，无法成功触发。

后来改用 WinterBreak2，最终成功。

参考教程：

[KindleModding — WinterBreak2](https://kindlemodding.org/jailbreaking/WinterBreak2/?utm_source=chatgpt.com)

操作过程：

1. 在电脑上下载 `wb2.zip`。
2. 解压压缩包。
3. 通过 USB 将 Kindle 连接 Windows。
4. 将解压出的 `winterbreak2` 文件夹复制到 Kindle 根目录。
5. 安全弹出 Kindle。

目录示意：

```
Kindle (F:)
├── documents/
├── winterbreak2/
└── ...
```

### Step 4：通过 Kindle Browser 启动越狱

在 Kindle 主界面点击右上角三个点：

`Web Browser`

然后：

1. 关闭飞行模式。
2. 连接家庭 Wi-Fi。
3. 在 Kindle 浏览器输入：

   [WinterBreak2 启动页面](https://penguins184.xyz/wb2?utm_source=chatgpt.com)
4. 等待页面显示 `WinterBreak2`。
5. 点击 Jailbreak。
6. 等待执行完成并自动重启。

我们当时看到的关键日志：

```
Running KMC System Patcher
Patching old hotfix
Running system patch script
Done
Restarting Kindle...
```

重启后 Library 出现：

`JAILBROKEN`

打开文档可以看到：

```
You are jailbroken!
(jb.sh v2.6.0)

Winterbreak2 Jailbreak
```

这就是我们实际验证成功的标志。

越狱成功后不需要再次运行 WinterBreak2，也不要恢复出厂设置。

## 三、安装 KUAL

KUAL 全称 Kindle Unified Application Launcher，是启动第三方 Kindle 程序的菜单系统。

### Step 5：下载 KUAL / PEKI

我们使用了 PEKI 提供的 KUAL 启动方式。

下载地址：

[PEKI — GitHub Releases](https://github.com/KindleTweaks/PEKI/releases?utm_source=chatgpt.com)

下载并解压后，使用：

```
KUAL.jar
KUAL.sh
```

### Step 6：复制到 Kindle

通过 USB 连接 Kindle，把两个文件放到：

```
F:\documents\
    KUAL.jar
    KUAL.sh
```

安全弹出 USB。

等待 Kindle 重新扫描文档，必要时重新启动 Kindle。

随后 Library 出现 KUAL 图标。

点击后，我们成功进入 KUAL 菜单，底部显示：

```
18b218e (20250103,a) - KT3
```

这证明 KUAL 已经正常运行，并识别出 KT3 设备。

## 四、安装 Kindle Dashboard 插件

### Step 7：下载 Dashboard

我们使用的项目：

[ZEUSGMJ / kindle-homelab-dashboard](https://github.com/ZEUSGMJ/kindle-homelab-dashboard?utm_source=chatgpt.com)

项目包含：

```
kindle-homelab-dashboard/
├── docker-compose.yml
├── requirements.txt
├── server/
├── kindle-extension/
├── images/
└── README.md
```

其中：

- `server/`：Python 图片生成和 HTTP 服务。
- `kindle-extension/`：Kindle 端 KUAL 插件。
- `docker-compose.yml`：服务器 Docker 部署配置。

### Step 8：安装 Kindle 扩展

将项目中的 `kindle-extension` 目录复制到 Kindle：

```
F:\extensions\kindle-dashboard\
```

编辑其中的：

`config.sh`

设置服务器地址：

```
DASHBOARD_BASE_URL="http://192.168.86.37:8070"
FULL_REFRESH_EVERY=5
```

这里 `192.168.86.37` 是我们使用的 Mac Mini 局域网地址示例；实际部署时以 `hostname -I` 查到的 IP 为准。

完成后：

1. 安全弹出 Kindle。
2. 打开 Library → KUAL。
3. 出现 Homelab Dashboard。
4. 进入插件菜单，选择 Portrait 或 Landscape。

至此，Kindle 端安装完成。

## 五、Ubuntu 24.04 部署 Dashboard Server

### Step 9：下载服务器项目

在 Mac Mini 上执行：

```
cd ~

git clone https://github.com/ZEUSGMJ/kindle-homelab-dashboard.git

cd kindle-homelab-dashboard
```

### Step 10：配置服务器

创建 `.env`：

```
cp .env.example .env
nano .env
```

我们主要配置：

```
DASHBOARD_TITLE=Tommy Dashboard
DISPLAY_TZ=America/New_York

WEATHER_ENABLED=true
WEATHER_LOCATION=State College
WEATHER_LAT=40.7934
WEATHER_LON=-77.8600
WEATHER_TEMP_UNIT=fahrenheit
WEATHER_WIND_UNIT=mph
```

其他参数根据项目的 `.env.example` 保留或调整。

### Step 11：启动 Docker 服务

当时 Mac Mini 已安装 Docker，但缺少 Compose 插件，因此补装：

```
sudo apt update
sudo apt install -y docker-compose-v2
```

随后：

```
cd ~/kindle-homelab-dashboard

sudo docker compose up -d --build
```

检查：

```
sudo docker compose ps
```

成功状态：

```
kindle-homelab-dashboard
Up (healthy)
0.0.0.0:8070->8070/tcp
```

健康检查：

```
curl http://localhost:8070/healthz
```

返回：

```
ok
```

### Step 12：浏览器预览

在 Windows 浏览器访问：

```
http://MAC_MINI_IP:8070/preview
```

横屏：

```
http://MAC_MINI_IP:8070/preview/landscape
```

这些地址用于在电脑上检查布局，不需要反复在 Kindle 上测试。

## 六、修正 Kindle KT3 屏幕分辨率

这是我们实际遇到的最重要兼容性问题。

原 Dashboard 主要针对 Kindle Paperwhite 2，分辨率比 KT3 高。

| 模式        | 原版       | KT3     |
| --------- | -------- | ------- |
| Portrait  | 758×1024 | 600×800 |
| Landscape | 1024×758 | 800×600 |

### Step 13：修改图片尺寸

文件：

`server/render_dashboard.py`

关键参数：

```
WIDTH, HEIGHT = 600, 800LANDSCAPE_WIDTH, LANDSCAPE_HEIGHT = 800, 600
```

另外，在：

`server/serve_dashboard.py`

将网页预览尺寸同步改成 600×800 和 800×600。

但我们发现，只改分辨率还不够。

原程序内部仍然使用针对 1024×758 的固定坐标，例如：

```
left_width = 646rail_x = 714
```

在 800 像素宽的 KT3 上，天气栏会被裁切。

因此我们进一步调整了标题字体、Containers 区域、天气栏位置、磁盘区域和 Footer 坐标。

最终横屏成功显示：

- 标题和时间
- CPU / MEM / TEMP / LOAD / SWAP
- Containers
- State College 天气
- Disk

这部分属于 KT3 的必要布局适配。重新部署原版项目时，需要保留我们修改过的布局代码，否则裁切问题会再次出现。

## 七、安装 Glances 系统监控

### Step 14：安装 Glances

Glances 用来获取 Mac Mini 的真实系统状态。

我们采用 Python 虚拟环境安装：

```
sudo apt install -y python3-venv python3-pip lm-sensors

python3 -m venv ~/glances-venv

~/glances-venv/bin/pip install 'glances[web,docker]'
```

启动：

```
~/glances-venv/bin/glances -w -B 0.0.0.0
```

成功后显示：

```
Glances 4.5.9

Web UI:
http://0.0.0.0:61208/

REST API:
http://0.0.0.0:61208/api/4
```

Dashboard 自动获得了系统数据，因此当时不需要额外修改 Docker 网络设置。

我们成功显示：

| 指标          | 当时结果 |
| ----------- | ---- |
| CPU         | 3%   |
| Memory      | 11%  |
| Temperature | 44°C |
| Load        | 7.8  |
| Swap        | 0%   |
| Disk        | 14%  |
| Containers  | 0/0  |

`Containers` 用来监控 Docker 容器，不是天气数据。由于没有获取到容器信息，当时显示 `0/0`。

### Step 15：Glances 开机启动

我们讨论了将 Glances 配置为 systemd 服务，建议使用：

```
/etc/systemd/system/glances.service
```

通过 `ExecStart` 调用虚拟环境中的 Glances，并配置自动重启。

启用命令：

```
sudo systemctl daemon-reload
sudo systemctl enable --now glances
```

检查：

```
systemctl is-enabled glances
systemctl is-active glances
```

这一步是推荐的长期运行配置；对话中没有收到你最终执行成功的日志，因此不把它记作已验证完成。

Glances 默认无认证运行时存在安全风险。长期部署应限制 61208 端口的访问范围。

## 八、最终结果与注意事项

已实际验证成功

- WinterBreak2 越狱成功。
- KUAL 能正常启动。
- Homelab Dashboard 出现在 KUAL 菜单。
- Mac Mini Dashboard 服务健康检查通过。
- Windows 浏览器可预览 Dashboard。
- Kindle 能通过 Wi-Fi 显示 Dashboard。
- KT3 横屏 800×600 布局适配成功。
- Glances CPU、内存、温度、磁盘等数据成功显示。

### 需要特别记住的几个问题

1. 不要随便升级 Kindle 固件。 当前成功环境是 KT3 + 5.16.2.1.1。
2. 未注册 Kindle 可以使用 WinterBreak2。 我们最初尝试的 WinterBreak Store 方式没有成功。
3. KUAL 是启动器，不是 Dashboard 本身。 Dashboard 扩展放在 `extensions` 目录。
4. KT3 必须适配分辨率和布局。 原版 Paperwhite 2 的固定坐标会导致裁切。
5. Dashboard 全屏运行时，触摸屏不一定有效。 我们曾遇到退出后白屏，后来恢复了 Kindle 原生界面。重新测试前应确认退出机制可靠。
6. Glances 和 Docker 是服务器端组件。 Kindle 本身只负责下载并显示生成的图片。

## 九、关键链接汇总

| 用途           | 地址                                                                                              |
| ------------ | ----------------------------------------------------------------------------------------------- |
| 越狱指南         | [WinterBreak2](https://kindlemodding.org/jailbreaking/WinterBreak2/?utm_source=chatgpt.com)     |
| 越狱启动页面       | [WinterBreak2 Web](https://penguins184.xyz/wb2?utm_source=chatgpt.com)                          |
| KUAL 启动器     | [PEKI Releases](https://github.com/KindleTweaks/PEKI/releases?utm_source=chatgpt.com)           |
| Dashboard 源码 | [Homelab Dashboard](https://github.com/ZEUSGMJ/kindle-homelab-dashboard?utm_source=chatgpt.com) |
| 系统监控         | [Glances](https://github.com/nicolargo/glances?utm_source=chatgpt.com)                          |

最终成果： 一台 Kindle 8th Generation（KT3）通过 WinterBreak2 越狱，安装 KUAL 和 Homelab Dashboard，连接 Ubuntu 24.04 Mac Mini 上的服务，成功实现了 800×600 横屏电子墨水天气及系统监控显示。

后续你自己对 Dashboard 应用所做的修改不包含在这份总结中。
