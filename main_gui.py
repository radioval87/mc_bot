import asyncio
import datetime
import json
import logging

import aiofiles
import configargparse

import gui
from common import MessageFormatError, manage_socket, write_to_socket


async def save_messages(filepath, queue):
    msg = await queue.get()
    async with aiofiles.open(filepath, mode='a') as f:
        await f.write(msg)


async def load_history(filepath, messages_queue):
    async with aiofiles.open(filepath, mode='r') as f:
        msgs = await f.read()
        for msg in msgs.split('\n'):
            messages_queue.put_nowait(msg)


async def submit_message(host, port, sending_queue):
    async with manage_socket(host, port) as (reader, writer):
        await read_from_chat(reader)
        await login(reader, writer)
        while True:
            message = await sending_queue.get()
            await write_to_socket(writer, [message, '\n', '\n'])
            logging.debug(f'Sent message: {message}')


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


def exit_on_token_error():
    print('Unknown token. Check it or register again.')
    raise SystemExit


async def process_token():
    try:
        async with aiofiles.open('.token', mode='r') as f:
            token = await f.read()
    except FileNotFoundError:
        logging.error('File with token was not found')  
    return token


async def read_from_chat(reader):
    msg = await reader.read(1000)
    logging.debug(msg.decode())
    return msg


async def login(reader, writer):    
    token = await process_token()
    try:
        await write_to_socket(writer, [token, '\n'])
    except MessageFormatError:
        exit_on_token_error()

    answer = await read_from_chat(reader)
    answer = answer.decode().split('\n')[0]
    
    answer = json.loads(answer)
    try:
        if not answer:
            exit_on_token_error()
    except Exception as e:
        logging.error(f'Error loading token: {str(e)}')
        raise SystemExit

    logging.debug(f'Выполнена авторизация. Пользователь {answer["nickname"]}.')


async def main(host, port, writer_port, history_path):
    messages_queue = asyncio.Queue()
    messages_history_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()

    await asyncio.gather(
        gui.draw(messages_queue, sending_queue, status_updates_queue),
        read_msgs(host, port, history_path, messages_queue, messages_history_queue),
        submit_message(host, writer_port, sending_queue)
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
        '--writer_port', type=int, help='Writer Host port', env_var='WRITER_PORT',
        default=5050
    )
    parser.add_argument(
        '--history', type=str, default='./log.txt',
        help='Path to the log file', env_var='HISTORY_PATH'
    )

    args = parser.parse_args()

    logging.basicConfig(
        format=(
            '%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s] '
            '%(message)s'
        ),
        level=logging.DEBUG
    )

    asyncio.run(main(args.host, args.port, args.writer_port, args.history), debug=True)
