import asyncio
import datetime

import aiofiles
import configargparse

from common import socket_manager


async def display_chat(host, port, history):
    async with socket_manager(host, port) as (reader, _):

        while True:
            async with aiofiles.open(history, mode='a') as f:

                data = await reader.read(1000)
                timestamp = datetime.datetime.now().strftime("%d.%m.%y %H.%M")
                message = f'[{timestamp}] '

                try:
                    message += data.decode()
                    print(message)
                    await f.write(message)
                except Exception as e:
                    message += str(e)
                    print(message)


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
