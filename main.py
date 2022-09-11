import asyncio
import datetime

import aiofiles
import configargparse


async def tcp_echo_client(host, port, history):
    reader, _ = await asyncio.open_connection(
        host, port)

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
        help='Host address', env_var='HOST', default='minechat.dvmn.org')
    parser.add_argument(
        '--port', type=int, help=('Host port'), env_var='PORT', default=5000
    )
    parser.add_argument(
        '--history', type=str, default='./log.txt',
        help='Path to the log file', env_var='HISTORY_PATH'
    )
    args = parser.parse_args()

    asyncio.run(tcp_echo_client(args.host, args.port, args.history))
