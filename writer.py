import asyncio
import json
import logging

import aiofiles
import configargparse

from common import MessageFormatError, manage_socket, write_to_socket


def exit_on_token_error():
    print('Unknown token. Check it or register again.')
    raise SystemExit


async def read_from_chat(reader):
    msg = await reader.read(1000)
    logging.debug(msg.decode())
    return msg


async def process_token(token):
    if not token:
        try:
            async with aiofiles.open('.token', mode='r') as f:
                token = await f.read()
        except FileNotFoundError:
            logging.error('File with token was not found')  
    return token


async def login(reader, writer, token):
    token = await process_token(token)
    try:
        await write_to_socket(writer, [token, '\n'])
    except MessageFormatError:
        exit_on_token_error()

    answer = await read_from_chat(reader)
    answer = answer.decode().split('\n')[0]
    
    try:
        if not json.loads(answer):
            exit_on_token_error()
    except Exception as e:
        logging.error(f'Error loading token: {str(e)}')
        raise SystemExit

    logging.debug('Logged in successfully')


async def submit_message(host, port, token, message):
    async with manage_socket(host, port) as (reader, writer):
        await read_from_chat(reader)
        await login(reader, writer, token)
        await write_to_socket(writer, [message, '\n', '\n'])
        logging.debug(f'Sent message: {message}')


if __name__ == '__main__':
    parser = configargparse.ArgParser()
    parser.add_argument(
        '--host', type=str, help='Host address',
        env_var='WRITER_HOST', default='minechat.dvmn.org'
    )
    parser.add_argument(
        '--port', type=int, help='Host port', env_var='WRITER_PORT',
        default=5050
    )
    parser.add_argument(
        '--token', type=str,
        help='Personal hash to connect as an existing user', env_var='TOKEN'
    )
    parser.add_argument(
        '--message', type=str,
        help='Message to send', required=True
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
