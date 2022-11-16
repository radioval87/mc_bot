import asyncio
import datetime
import json
import logging
import time
from tkinter import messagebox

import aiofiles
import async_timeout
import configargparse
from anyio import create_task_group
from exceptiongroup import catch

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


async def handle_connection(host, port, history_path, messages_queue, messages_history_queue, status_updates_queue, watchdog_queue, sending_queue):
    async with manage_socket(host, port) as (reader, writer):
        while True:
            async with create_task_group() as tg:
                tg.start_soon(read_msgs, reader, writer, history_path, messages_queue, messages_history_queue, status_updates_queue, watchdog_queue)
                tg.start_soon(submit_message, reader, writer, sending_queue, status_updates_queue, watchdog_queue)


async def submit_message(reader, writer, sending_queue, status_updates_queue, watchdog_queue):
    await read_from_chat(reader)
    watchdog_queue.put_nowait('Connection is alive. Prompt before auth')
    await login(reader, writer, status_updates_queue, watchdog_queue)
    status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.ESTABLISHED)
    while True:
        message = await sending_queue.get()
        await write_to_socket(writer, [message, '\n', '\n'])
        logging.debug(f'Sent message: {message}')
        watchdog_queue.put_nowait('Connection is alive. Message sent')
        

async def read_msgs(reader, writer, history_path, messages_queue, messages_history_queue, status_updates_queue, watchdog_queue):
    await load_history(history_path, messages_queue)
    while True:
        try:
            async with async_timeout.timeout(1) as cm:
                chat_message = await read_from_chat(reader)
            status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.ESTABLISHED)
            status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.ESTABLISHED)
            watchdog_queue.put_nowait('Connection is alive. New message in chat')
        except asyncio.TimeoutError:
            if cm.expired:
                watchdog_queue.put_nowait('1s timeout is elapsed')
            # status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.CLOSED)
            # status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.CLOSED)
            chat_message = None
        timestamp = datetime.datetime.now().strftime("%d.%m.%y %H.%M")

        if chat_message:
            try:
                # chat_message = chat_message.decode()
                formatted_message = f'[{timestamp}] {chat_message}'
                messages_queue.put_nowait(formatted_message)
                messages_history_queue.put_nowait(formatted_message)
                await save_messages(history_path, messages_history_queue)
            except Exception as e:
                formatted_message = f'[{timestamp}] {str(e)}'
                messages_queue.put_nowait(formatted_message)


def exit_on_token_error():
    print('Unknown token. Check it or register again.')
    messagebox.showerror("Error", "Unknown token. Check it or register again.")
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
    decoded_msg = msg.decode()
    logging.debug(decoded_msg)
    return decoded_msg


async def login(reader, writer, status_updates_queue, watchdog_queue):    
    token = await process_token()
    try:
        await write_to_socket(writer, [token, '\n'])
    except MessageFormatError:
        exit_on_token_error()

    answer = await read_from_chat(reader)
    answer = answer.split('\n')[0]
    
    answer = json.loads(answer)
    try:
        if not answer:
            exit_on_token_error()
    except Exception as e:
        logging.error(f'Error loading token: {str(e)}')
        raise SystemExit

    logging.debug(f'Выполнена авторизация. Пользователь {answer["nickname"]}.')
    event = gui.NicknameReceived(answer["nickname"])
    status_updates_queue.put_nowait(event)
    watchdog_queue.put_nowait('Connection is alive. Authorization done')


async def watch_for_connection(watchdog_queue):
    while True:
        logger = logging.getLogger('watchdog_logger')
        message = await watchdog_queue.get()
        logger.info(f'[{time.time()}] {message}')
        if message == '1s timeout is elapsed':
            raise ConnectionError


async def main(host, port, writer_port, history_path):
    messages_queue = asyncio.Queue()
    messages_history_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()
    watchdog_queue = asyncio.Queue()

    status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.INITIATED)
    status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.INITIATED)

    def handle_connection_error(exc: ConnectionError) -> None:
        status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.CLOSED)
        status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.CLOSED)

    with catch({ConnectionError: handle_connection_error}):
        async with create_task_group() as tg:
            tg.start_soon(gui.draw, messages_queue, sending_queue, status_updates_queue)
            tg.start_soon(handle_connection, host, port, history_path, messages_queue, messages_history_queue, status_updates_queue, watchdog_queue, sending_queue)
            # tg.start_soon(submit_message, host, writer_port, sending_queue, status_updates_queue, watchdog_queue)
            # tg.start_soon(read_msgs, reader, writer, history_path, messages_queue, messages_history_queue, status_updates_queue, watchdog_queue)
            tg.start_soon(watch_for_connection, watchdog_queue)


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

    asyncio.run(main(args.host, args.port, args.writer_port, args.history))
