import asyncio
import datetime

import aiofiles
import configargparse

from common import socket_manager


async def display_chat(host, port, history):
    async with socket_manager(host, port) as (reader, _):

        while True:
            async with aiofiles.open(history, mode='a') as f:

                chat_message = await reader.read(1000)
                timestamp = datetime.datetime.now().strftime("%d.%m.%y %H.%M")

                try:
                    chat_message = chat_message.decode()
                    formatted_message = f'[{timestamp}] {chat_message}'
                    print(formatted_message)
                    await f.write(formatted_message)
                except Exception as e:
                    formatted_message = f'[{timestamp} {str(e)}] '
                    print(formatted_message)


if __name__ == '__main__':
    parser = configargparse.ArgParser()
    parser.add_argument('--host', type=str,
        help='Host address', env_var='MAIN_HOST', default='minechat.dvmn.org')
    parser.add_argument(
        '--port', type=int, help=('Host port'), env_var='MAIN_PORT',
        default=5000
    )
    parser.add_argument(
        '--history', type=str, default='./log.txt',
        help='Path to the log file', env_var='HISTORY_PATH'
    )
    args = parser.parse_args()

    asyncio.run(display_chat(args.host, args.port, args.history))
