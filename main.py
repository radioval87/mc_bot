import asyncio
import datetime

import aiofiles


async def tcp_echo_client():
    reader, _ = await asyncio.open_connection(
        'minechat.dvmn.org', 5000)

    while True:
        async with aiofiles.open('log.txt', mode='a') as f:

            data = await reader.read(100)
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
    asyncio.run(tcp_echo_client())
