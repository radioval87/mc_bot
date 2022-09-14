import asyncio
import json
import logging

import configargparse

from common import socket_manager


async def read_and_save_to_log(reader):
    msg = await reader.read(1000)
    logging.debug(msg.decode())
    return msg


async def process_token(token):
    if not token:
        try:
            with open('.token', mode='r') as f:
                token = f.read()
        except Exception as e:
            logging.warning(f'Токен не найден. {str(e)}')

    token = f'{token}\n'
    return token


async def login(reader, writer, token):
    token = await process_token(token)
    writer.write(token.encode())
    writer.drain()

    answer = await read_and_save_to_log(reader)
    answer = answer.decode().split('\n')[0]
    
    try:
        if not json.loads(answer):
            logging.warning('Неизвестный токен. ' 
                            'Проверьте его или зарегистрируйте заново.')
            raise SystemExit
    except Exception as e:
        logging.error(f'Ошибка загрузки токена: {str(e)}')


async def submit_message(host, port, token, message):
    async with socket_manager(host, port) as (reader, writer):

        await read_and_save_to_log(reader)

        await login(reader, writer, token)

        writer.write(message.encode())
        writer.write('\n'.encode())
        writer.write('\n'.encode())
        writer.drain()
        logging.debug(f'Sent message: {message}')


if __name__ == '__main__':
    parser = configargparse.ArgParser()
    parser.add_argument(
        '--host', type=str, help='Host address',
        env_var='WRITER_HOST', default='minechat.dvmn.org'
    )
    parser.add_argument(
        '--port', type=int, help=('Host port'), env_var='WRITER_PORT',
        default=5050
    )
    parser.add_argument(
        '--token', type=str,
        help='Personal hash to connect as an existing user', env_var='TOKEN'
    )
    parser.add_argument(
        '--message', type=str,
        help='Message to send on connecting', required=True
    )
    args = parser.parse_args()

    logging.basicConfig(
        format=(
            '%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s] '
            '%(message)s'
        ),
        level=logging.DEBUG
    )

    asyncio.run(submit_message(args.host, args.port, args.token, args.message))
