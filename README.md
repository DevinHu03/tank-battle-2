# 钢铁防线

简体中文单人坦克战役游戏。五张手工地图依次包含歼灭、守卫、生存、护送和 Boss 任务；一局完整战役约 25–35 分钟。

## 启动

需要 Python 3.11+。

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## 操作

- `WASD` 或方向键：移动和转向
- `Space`：射击
- `Enter`：确认
- `Esc`：暂停或返回
- `M`：快速静音
- `F11`：窗口/全屏切换
- '技能选择按数字键’

## 测试

```powershell
$env:SDL_VIDEODRIVER='dummy'
$env:SDL_AUDIODRIVER='dummy'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

规则层不依赖显示器或音频设备，覆盖地形、战役任务、Boss 阶段、升级与版本化存档。存档默认写入项目旁的 `save.json`；发行版首次启动时自动创建它。

## Windows 打包

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm build\SteelFrontline.spec
Compress-Archive -Path release\SteelFrontline\* -DestinationPath release\SteelFrontline-Windows.zip -Force
```

生成的 `release\SteelFrontline\SteelFrontline.exe` 不需要目标电脑安装 Python。请勿将个人 `save.json` 放入发行 ZIP。

素材与声音使用项目内原创资源：复古街机菜单、地形/道具图集和 `assets\music\steel_frontline_theme.wav`。第 4 关现为“废墟突袭”歼灭任务，不再使用有路线卡死风险的护送载具流程。
