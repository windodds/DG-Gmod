import asyncio
import websockets
import json
import traceback
from utils import *
from config import DEFAULT_CONFIG

my_logger = Logger()

class GmodReceiver:
    def __init__(self, dghub_ws):
        self.config = dict(DEFAULT_CONFIG)
        self.dghub_ws = dghub_ws
        
        self.pending_dmg = 0.0
        self.reset_time = 2.0
        self.flush_task = None
        
    def init_update(self, msg):
        self.config.update(msg["data"])

    def user_update(self, msg):
        self.config[msg["key"]] = msg["value"]

    async def handler(self, gmod_ws):
        my_logger.log(f"客户端已连接: {gmod_ws.remote_address}")
        try:
            async for msg in gmod_ws:
                try:
                    data = json.loads(msg)
                    my_logger.log(f"收到 GMod 数据: {data}")
                    await self.data_received(data)
                except Exception:
                    pass
        except websockets.ConnectionClosed:
            my_logger.log(f"客户端断开: {gmod_ws.remote_address}")
        except Exception as e:
            my_logger.log(e, "error", traceback.format_exc())

    async def schedule_flush(self):
        if self.flush_task and not self.flush_task.done():
            self.flush_task.cancel()
        self.flush_task = asyncio.create_task(self.flush())

    async def flush(self):
        try:
            await asyncio.sleep(self.config["damage_stack_time"])
        except asyncio.CancelledError:
            return
        self.pending_dmg = 0.0
        asyncio.create_task(self.reset_baseline())
        
    async def data_received(self, data):
        id = data["ply_id"]
        event = data["event"]

        # 多人模式
        if self.config["multi_player"]:
            try:
                if id != int(self.config["steamid64"]):
                    return
            except:
                return
                
        if event == "damage" and self.config["damage_penalty"]:
            damage_type = data["dmg_type"]

            damage_amount = data["dmg_amount"]
            delta = min(float(damage_amount), float(self.config["damage_cap"])) # 处理伤害上限
            delta_real = delta * self.config["damage_multiplier"] + self.config["damage_increment"]
            
            duration = float(self.config["damage_duration"])
            channel = self.config["channel_damage"]

            if self.config["damage_stacking"]: # 伤害累加
                if self.config["damage_any"] and damage_type == "any":
                    self.pending_dmg += delta_real
                elif self.config["damage_burn"] and damage_type == "burn":
                    self.pending_dmg += delta_real
                elif self.config["damage_blast"] and damage_type == "blast":
                    self.pending_dmg += delta_real
                if self.pending_dmg > self.config["damage_stacking_cap"]:
                    delta_real = 0                    
                asyncio.create_task(self.send_stacked_shock(delta_real, duration, channel))
                await self.schedule_flush()
                return
            
            if self.config["damage_any"] and damage_type == "any":
                preset = self.config["damage_any_preset"]
                label = "Gmod 受伤"
            elif self.config["damage_burn"] and damage_type == "burn":
                preset = self.config["damage_burn_preset"]
                label = "Gmod 燃烧"
            elif self.config["damage_blast"] and damage_type == "blast":
                preset = self.config["damage_blast_preset"]
                label = "Gmod 爆炸"
            asyncio.create_task(self.send_shock(delta_real, duration, preset, channel, label))

        elif event == "death" and self.config["death_penalty"]:
            delta = self.config["death_penalty_pct"]
            duration = float(self.config["death_penalty_duration"])
            preset = self.config["death_preset"]
            channel = self.config["channel_death"]
            label = "Gmod 死亡"
            asyncio.create_task(self.reset_baseline())
            asyncio.create_task(self.send_shock(delta, duration, preset, channel, label))

    async def send_stacked_shock(self, delta, duration, channel):
        delta_pct = min(int(delta), 100)
        preset = "CS-受伤"
        label = "Gmod 合并"
        payload = {
                    "op": "trigger",
                    "action": "both",
                    "delta_pct": delta_pct,
                    "strength_mode": "permanent",
                    "duration_s": duration, 
                    "preset": preset,
                    "channel": channel,
                    "label": label
                }
        try:
            await self.dghub_ws.send(json.dumps(payload, ensure_ascii=False))
            await send_log(self.dghub_ws, f"[DG-GMOD] 指令已发出: {label}")

        except websockets.ConnectionClosed:
            pass

    async def reset_baseline(self):
        label = "清零"
        payload = {
                    "op": "trigger",
                    "action": "both",
                    "delta_pct": -100,
                    "strength_mode": "permanent",
                    "duration_s": 0, 
                    "preset": "CS2-受伤",
                    "channel": "both",
                    "label": label
                }
        try:
            await self.dghub_ws.send(json.dumps(payload, ensure_ascii=False))             
            await send_log(self.dghub_ws, f"[DG-GMOD] 指令已发出: {label}")
        except websockets.ConnectionClosed:
            pass

    async def send_shock(self, delta, duration, preset, channel, label, mode="rollback"):
        delta_pct = min(int(delta), 100)
        payload = {
                    "op": "trigger",
                    "action": "both",
                    "delta_pct": delta_pct,
                    "strength_mode": mode,
                    "duration_s": duration, 
                    "preset": preset,
                    "channel": channel,
                    "label": label
                }
        try:
            await self.dghub_ws.send(json.dumps(payload, ensure_ascii=False))
            await send_log(self.dghub_ws, f"[DG-GMOD] 指令已发出: {label}")
        except websockets.ConnectionClosed:
            pass

    async def run_server(self):
        host = "0.0.0.0"
        port = 8770
        url = f"ws://{host}:{port}"
        self.server = await websockets.serve(self.handler, host, port)
        my_logger.log(f"服务器运行在: {url}")
