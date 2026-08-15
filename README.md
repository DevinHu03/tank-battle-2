# 坦克大战 · HTY 战术闯关

单人、单地图的三波坦克战术小游戏。中央的不可摧毁红砖墙按 **HTY** 排列；利用掩体、击败不同敌军，并在 Boss 战中存活。

## 启动

需要 Python 3.11+。无需激活虚拟环境时可直接运行：

```powershell
.\.venv\Scripts\python.exe main.py
```

首次安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 操作

- `WASD` 或方向键：移动，移动方向同时决定炮塔方向
- `Space`：射击
- `Enter`：开始
- `R`：胜利或失败后从第一波重开
- `M`：静音/恢复音效
- `Esc`：退出

## 玩法

关卡为固定三波：高速轻装敌军、装甲敌军、狙击敌军会逐步混编；第三波由 14 点生命的重装齐射 Boss 收尾。敌军可能掉落以下本局强化：

- 生命：回复 1 点生命，最高 3 点
- 连发：8 秒内更快射击
- 护盾：8 秒内免疫伤害

每局会显示得分、波次、强化时间和 Boss 血条。击败 Boss 后按总分评为 S/A/B；最高分保存到项目根目录的 `save.json`。若存档或音频设备不可用，游戏仍可正常运行。

## 测试

```powershell
$env:SDL_VIDEODRIVER='dummy'
$env:SDL_AUDIODRIVER='dummy'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

玩家、侦察、装甲、狙击与 Boss 坦克均使用 AI 生成的透明俯视精灵；HTY 砖墙、HUD 和粒子由代码绘制。音频包含合成的循环背景音乐与战斗效果音。
