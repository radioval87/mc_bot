import asyncio
import datetime

import aiofiles
import configargparse

import gui
from common import manage_socket


async def save_messages(filepath, queue):
    msg = await queue.get()
    async with aiofiles.open(filepath, mode='a') as f:
        await f.write(msg)


async def load_history(filepath, messages_queue):
    async with aiofiles.open(filepath, mode='r') as f:
        msgs = await f.read()
        for msg in msgs.split('\n'):
            messages_queue.put_nowait(msg)


async def read_msgs(host, port, history_path, messages_queue, messages_history_queue):
    async with manage_socket(host, port) as (reader, _):
        await load_history(history_path, messages_queue)
        while True:
            chat_message = await reader.read(1000)
            timestamp = datetime.datetime.now().strftime("%d.%m.%y %H.%M")

            try:
                chat_message = chat_message.decode()
                formatted_message = f'[{timestamp}] {chat_message}'
                messages_queue.put_nowait(formatted_message)
                messages_history_queue.put_nowait(formatted_message)
                await save_messages(history_path, messages_history_queue)
            except Exception as e:
                formatted_message = f'[{timestamp}] {str(e)}'
                messages_queue.put_nowait(formatted_message)


async def main(host, port, history_path):
    messages_queue = asyncio.Queue()
    messages_history_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()
    
    await asyncio.gather(
        gui.draw(messages_queue, sending_queue, status_updates_queue),
        read_msgs(host, port, history_path, messages_queue, messages_history_queue),
    )


if __name__ == '__main__':
    parser = configargparse.ArgParser()
    parser.add_argument('--host', type=str,
        help='Host address', env_var='MAIN_HOST', default='minechat.dvmn.org')
    parser.add_argument(
        '--port', type=int, help='Host port', env_var='MAIN_PORT',
        default=5000
    )
    parser.add_argument(
        '--history', type=str, default='./log.txt',
        help='Path to the log file', env_var='HISTORY_PATH'
    )

    args = parser.parse_args()

    asyncio.run(main(args.host, args.port, args.history), debug=True)
