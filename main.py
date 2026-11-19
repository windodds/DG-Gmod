"""
Gmod x dg-lab
"""

import asyncio
import traceback
from utils import *
from runtime import run
my_logger = Logger()

async def main() -> None:
    my_logger.clearLogFile()
    while True: 
        try:
            result = await run()
            if result == "stop":
                break
            if result == "fatal":
                break
        except Exception as e:
            my_logger.log(e, "error", traceback.format_exc())
     
if __name__ == "__main__":
    asyncio.run(main())
