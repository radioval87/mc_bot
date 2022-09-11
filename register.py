import asyncio
import json
import logging

import aiofiles
import configargparse


async def read_and_show_in_log(reader):
    msg = await reader.read(1000)
    logging.debug(msg.decode())
    return msg


async def register(host, port):
    reader, writer = await asyncio.open_connection(host, port)

    await read_and_show_in_log(reader)

    writer.write('\n'.encode())

    await read_and_show_in_log(reader)

    while True:
        message = input()
        writer.write(message.encode())
        writer.write('\n'.encode())
        
        if message:
            logging.debug(f'Sent message: {message}')
            answer = await read_and_show_in_log(reader)
            answer = answer.decode().split('\n')[0]

            try:
                answer = json.loads(answer)
                token = answer['account_hash']
                username = answer['nickname']

                async with aiofiles.open('.token', mode='w') as f:
                    await f.write(token)
                print(f'Вы успешно зарегистрированы как {username}')
            except Exception as e:
                print(f'Ошибка регистрации: {str(e)}')
            finally:
                break


if __name__ == '__main__':
    parser = configargparse.ArgParser()
    parser.add_argument(
        '--host', required=False, type=str, help='Host address',
        env_var='HOST', default='minechat.dvmn.org'
    )
    parser.add_argument(
        '--port', required=False, type=int, help=('Host port'),
        env_var='PORT', default=5050
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
