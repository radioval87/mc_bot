import asyncio
import datetime

import configargparse

import gui
from common import manage_socket


async def read_msgs(host, port, queue):
    async with manage_socket(host, port) as (reader, _):
            while True:
                chat_message = await reader.read(1000)
                timestamp = datetime.datetime.now().strftime("%d.%m.%y %H.%M")

                try:
                    chat_message = chat_message.decode()
                    formatted_message = f'[{timestamp}] {chat_message}'
                    queue.put_nowait(formatted_message)
                except Exception as e:
                    formatted_message = f'[{timestamp}] {str(e)}'
                    queue.put_nowait(formatted_message)


async def generate_msgs(queue):
    while True:
        msg = '--empty--'
        queue.put_nowait(msg)
        await asyncio.sleep(1)


async def main(host, port):
    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()

    await asyncio.gather(
        gui.draw(messages_queue, sending_queue, status_updates_queue),
        read_msgs(host, port, messages_queue),
    )


if __name__ == '__main__':
    parser = configargparse.ArgParser()
    parser.add_argument('--host', type=str,
        help='Host address', env_var='MAIN_HOST', default='minechat.dvmn.org')
    parser.add_argument(
        '--port', type=int, help='Host port', env_var='MAIN_PORT',
        default=5000
    )

    args = parser.parse_args()

    asyncio.run(main(args.host, args.port), debug=True)
