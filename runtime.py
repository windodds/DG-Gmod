import asyncio
import json
import os
import sys
import traceback
from gmod_server import GmodReceiver
from utils import *
from messages import MESSAGES

try:
    import websockets
except ImportError:
    print("缺少 websockets，请: pip install websockets", file=sys.stderr, flush=True)
    raise

my_logger = Logger()

async def run():
    host = os.environ["DGHUB_HOST"]
    port = os.environ["DGHUB_PORT"]
    token = os.environ["DGHUB_TOKEN"]
    uri = f"ws://{host}:{port}/ws/plugin?token={token}"

    root = plugin_root()
    manifest = load_manifest(root)

    gmod_receiver = None

    try:    
        async with websockets.connect(uri) as ws:
            await ws.send(
                json.dumps(
                    {
                        "op": "hello",
                        "token": token,
                        "manifest": {
                            "id": os.environ.get("DGHUB_PLUGIN_ID", manifest.get('id')),
                            "name": manifest.get('name'),
                            "version": manifest.get('version'),
                            "sdk": manifest.get('sdk'),
                            "capabilities": manifest.get('capabilities'),
                            "config_schema": manifest.get('config_schema')
                        },
                    },
                    ensure_ascii=False
                )
            )
            
            ack = json.loads(await ws.recv())
            if not ack.get("accepted"):
                reson = ack.get("reason", "hello rejected")
                my_logger.log(f"握手被拒绝: {reson}")
                return "fatal"
                
            # 发送启动检查
            await ws.send(json.dumps(MESSAGES["status"],ensure_ascii=False))

            # 启动Gmod服务器
            gmod_receiver = GmodReceiver(ws)
            try:
                await gmod_receiver.run_server()
            except Exception as e:
                await send_log(ws, e, "error")
                my_logger.log(e, "error", traceback.format_exc())
            
            async for raw in ws:
                try: 
                    msg = json.loads(raw)
                except:
                    continue
                if msg.get("op") == "config_changed": # 接收设置更新
                    gmod_receiver.user_update(msg)
                    await send_change_log(ws, msg)
                    
                elif msg.get("op") == "config": # 启动时应用用户历史设置
                    gmod_receiver.init_update(msg) 

                elif msg.get("op") == "stop":
                    return "stop"
                
    except websockets.ConnectionClosed as e:
        my_logger.log(e, "error", traceback.format_exc())
    except Exception as e:
        my_logger.log(e, "error", traceback.format_exc())
    finally:
        gmod_receiver.server.close()

