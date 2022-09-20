import asyncio
import json
import logging

import aiofiles
import configargparse

from common import manage_socket, write_to_socket


async def read_from_chat(reader):
    msg = await reader.read(1000)
    logging.debug(msg.decode())
    return msg


async def register(host, port):
    async with manage_socket(host, port) as (reader, writer):
        await read_from_chat(reader)
        await write_to_socket(writer, ['\n'])
        await read_from_chat(reader)

        while True:
            message = input()
            await write_to_socket(writer, [message, '\n'])

            if message:
                logging.debug(f'Sent message: {message}')
                answer = await read_from_chat(reader)
                answer = answer.decode().split('\n')[0]

                try:
                    answer = json.loads(answer)
                    token = answer['account_hash']
                    username = answer['nickname']

                    async with aiofiles.open('.token', mode='w') as f:
                        await f.write(token)
                    print(f'You are successfully registered as {username}')
                except Exception as e:
                    logging.error(f'Registration error: {str(e)}')
                    raise e
                finally:
                    break


if __name__ == '__main__':
    parser = configargparse.ArgParser()
    parser.add_argument(
        '--host', required=False, type=str, help='Host address',
        env_var='REG_HOST', default='minechat.dvmn.org'
    )
    parser.add_argument(
        '--port', required=False, type=int, help='Host port',
        env_var='REG_PORT', default=5050
    )
    args = parser.parse_args()

    logging.basicConfig(
        format=(
            '%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s] '
            '%(message)s'
        ),
        level=logging.DEBUG
    )

    asyncio.run(register(args.host, args.port))
