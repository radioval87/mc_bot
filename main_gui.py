import asyncio
import datetime
import json
import logging
import time
from socket import gaierror
from tkinter import messagebox

import aiofiles
import async_timeout
import configargparse
from anyio import ExceptionGroup, create_task_group
from exceptiongroup import catch

import gui
from common import MessageFormatError, manage_socket, write_to_socket


async def load_history(filepath, messages_queue):
    async with aiofiles.open(filepath, mode='r') as f:
        msgs = await f.read()
        for msg in msgs.split('\n'):
            messages_queue.put_nowait(msg)


async def ping_pong(reader, writer):
    
    try:
        async with async_timeout.timeout(1) as cm:
            await write_to_socket(writer, [''])
            await read_from_chat(reader)
    except asyncio.TimeoutError:
        raise gaierror
    await asyncio.sleep(1)


async def handle_connection(
    host, port, writer_port, history_path, messages_queue,
    messages_history_queue, status_updates_queue, watchdog_queue,
    sending_queue
):

    def handle_connection_error(exc: ConnectionError) -> None:
        status_updates_queue.put_nowait(
            gui.ReadConnectionStateChanged.CLOSED)
        status_updates_queue.put_nowait(
            gui.SendingConnectionStateChanged.CLOSED)

    def handle_gaierror_error(exc: gaierror) -> None:
        status_updates_queue.put_nowait(
            gui.ReadConnectionStateChanged.INITIATED)
        status_updates_queue.put_nowait(
            gui.SendingConnectionStateChanged.INITIATED)

    def handle_os_error(exc: OSError) -> None:
        status_updates_queue.put_nowait(
            gui.ReadConnectionStateChanged.INITIATED)
        status_updates_queue.put_nowait(
            gui.SendingConnectionStateChanged.INITIATED)

    while True:
        try:
            with catch({
                gaierror: handle_gaierror_error,
                ConnectionError: handle_connection_error,
                OSError: handle_os_error
            }):
                async with create_task_group() as tg:
                    tg.start_soon(watch_for_connection, watchdog_queue)
                    tg.start_soon(send_msgs, host, writer_port, sending_queue,
                        status_updates_queue, watchdog_queue)
                    tg.start_soon(read_msgs, host, port, history_path,
                        messages_queue, messages_history_queue,
                        status_updates_queue, watchdog_queue)
        except ExceptionGroup:
            await asyncio.sleep(1)


async def send_msgs(
    host, port, sending_queue, status_updates_queue, watchdog_queue
):

    async with manage_socket(host, port) as (reader, writer):
        await read_from_chat(reader)
        watchdog_queue.put_nowait('Connection is alive. Prompt before auth')
        await login(reader, writer, status_updates_queue, watchdog_queue)
        status_updates_queue.put_nowait(
            gui.SendingConnectionStateChanged.ESTABLISHED)
        while True:
            await ping_pong(reader, writer)
            message = await sending_queue.get()
            await write_to_socket(writer, [message, '\n', '\n'])
            logging.debug(f'Sent message: {message}')
            watchdog_queue.put_nowait('Connection is alive. Message sent')
        

async def read_msgs(
    host, port, history_path, messages_queue, messages_history_queue,
    status_updates_queue, watchdog_queue
):

    await load_history(history_path, messages_queue)

    async def save_message(file_, queue):
        msg = await queue.get()
        await file_.write(msg)
    
    async with aiofiles.open(history_path, mode='a') as history_file:
        while True:
            try:
                async with async_timeout.timeout(1) as cm:
                    async with manage_socket(host, port) as (reader, _):
                        chat_message = await read_from_chat(reader)
                status_updates_queue.put_nowait(
                    gui.ReadConnectionStateChanged.ESTABLISHED)
                status_updates_queue.put_nowait(
                    gui.SendingConnectionStateChanged.ESTABLISHED)
                watchdog_queue.put_nowait(
                    'Connection is alive. New message in chat')
            except asyncio.TimeoutError:
                if cm.expired:
                    watchdog_queue.put_nowait('1s timeout is elapsed')
                chat_message = None
            timestamp = datetime.datetime.now().strftime("%d.%m.%y %H.%M")

            if chat_message:
                try:
                    formatted_message = f'[{timestamp}] {chat_message}'
                    messages_queue.put_nowait(formatted_message)
                    messages_history_queue.put_nowait(formatted_message)
                    await save_message(history_file, messages_history_queue)
                except Exception as e:
                    formatted_message = f'[{timestamp}] {str(e)}'
                    messages_queue.put_nowait(formatted_message)


def exit_on_token_error():
    print('Unknown token. Check it or register again.')
    messagebox.showerror(
        "Error", "Unknown token. Check it or register again.")
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
    answer = await read_from_chat(reader)

    token = await process_token()
    try:
        await write_to_socket(writer, [token, '\n'])
    except MessageFormatError:
        exit_on_token_error()
    
    answer = await read_from_chat(reader)

    try:
        answer = answer.split('\n')[0]
        answer = json.loads(answer)
        if not answer:
            exit_on_token_error()
    except Exception as e:
        logging.error(f'Error loading token: {str(e)}')
        raise SystemExit

    logging.debug(
        f'Выполнена авторизация. Пользователь {answer["nickname"]}.')
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

    status_updates_queue.put_nowait(
        gui.ReadConnectionStateChanged.INITIATED)
    status_updates_queue.put_nowait(
        gui.SendingConnectionStateChanged.INITIATED)

    try:
        async with create_task_group() as tg:
            tg.start_soon(gui.draw, messages_queue, sending_queue,
                status_updates_queue)
            tg.start_soon(handle_connection, host, port, writer_port,
                history_path, messages_queue, messages_history_queue,
                status_updates_queue, watchdog_queue, sending_queue)

    except gui.TkAppClosed:
        logging.info("Exit the app")


if __name__ == '__main__':
    parser = configargparse.ArgParser()
    parser.add_argument('--host', type=str,
        help='Host address', env_var='MAIN_HOST', default='minechat.dvmn.org')
    parser.add_argument(
        '--port', type=int, help='Host port', env_var='MAIN_PORT',
        default=5000
    )
    parser.add_argument(
        '--writer_port', type=int, help='Writer Host port',
        env_var='WRITER_PORT', default=5050
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

    try:
        asyncio.run(
            main(args.host, args.port, args.writer_port, args.history)
        )
    except KeyboardInterrupt:
        logging.info("Exit the app with CTRL+C")
