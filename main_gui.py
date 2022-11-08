import asyncio
import time
import gui


async def generate_msgs(queue):
    while True:
        msg = time.time()
        queue.put_nowait(msg)
        await asyncio.sleep(1)


async def main():
    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()

    await asyncio.gather(
        gui.draw(messages_queue, sending_queue, status_updates_queue),
        generate_msgs(messages_queue),
    )
    
asyncio.run(main(), debug=True)
