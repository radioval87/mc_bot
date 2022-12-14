import asyncio
import datetime
import json
import logging
import time
from functools import partial
from socket import gaierror
from tkinter import messagebox

import aiofiles
import async_timeout
import configargparse
from anyio import ExceptionGroup, create_task_group
from exceptiongroup import catch

import gui
from common import MessageFormatError, manage_socket

logger = logging.getLogger('watchdog_logger')
watchdog_logger = logging.getLogger('watchdog_logger')


def set_both_statuses(status_updates_queue, status):
    status_updates_queue.put_nowait(
        gui.ReadConnectionStateChanged.__members__.get(status))
    status_updates_queue.put_nowait(
        gui.SendingConnectionStateChanged.__members__.get(status))


async def write_to_socket(writer, messages):
    try:
        for message in messages:
            writer.write(message.encode())
    except AttributeError:
        raise MessageFormatError
    await writer.drain()


async def read_from_socket(reader):
    chat_message = await reader.read(1000)
    decoded_msg = chat_message.decode()
    logger.debug(decoded_msg)
    return decoded_msg


async def load_history(filepath, messages_queue):
    try:
        async with aiofiles.open(filepath, mode='r') as f:
            msgs = await f.read()
            for msg in msgs.split('\n'):
                messages_queue.put_nowait(msg)
    except FileNotFoundError:
        logger.error(f'File not found: {filepath}')


async def ping_pong(w_reader, w_writer):
    while True:
        try:
            async with async_timeout.timeout(1):
                await write_to_socket(w_writer, [''])
                await read_from_socket(w_reader)
        except asyncio.TimeoutError:
            raise gaierror
        await asyncio.sleep(1)


def handle_gaierror_error(status_updates_queue, exc: gaierror):
    set_both_statuses(status_updates_queue, 'INITIATED')


def handle_os_error(status_updates_queue, exc: OSError):
    set_both_statuses(status_updates_queue, 'INITIATED')


async def handle_connection(
    host, port, writer_port, history_path, messages_queue,
    messages_history_queue, status_updates_queue, watchdog_queue,
    sending_queue
):

    await load_history(history_path, messages_queue)

    while True:
        try:
            with catch({
                gaierror: partial(handle_gaierror_error,
                                  status_updates_queue),
                OSError: partial(handle_os_error,
                                 status_updates_queue)
            }):
                async with manage_socket(host, writer_port) as (
                    w_reader, w_writer):
                    async with manage_socket(host, port) as (r_reader, _):

                        await login(w_reader, w_writer, status_updates_queue,
                            watchdog_queue)

                        async with create_task_group() as tg:
                            tg.start_soon(send_msgs,
                                w_writer, sending_queue,
                                watchdog_queue
                            )
                            tg.start_soon(read_msgs,
                                r_reader, history_path,
                                messages_queue, messages_history_queue,
                                status_updates_queue, watchdog_queue
                            )
                            tg.start_soon(ping_pong, w_reader, w_writer)
        except ExceptionGroup:
            await asyncio.sleep(1)


async def send_msgs(w_writer, sending_queue, watchdog_queue):
    while True: 
        message = await sending_queue.get()
        await write_to_socket(w_writer, [message, '\n', '\n'])
        logger.debug(f'Sent message: {message}')
        watchdog_queue.put_nowait('Connection is alive. Message sent')


async def save_message(history_path, queue):
    async with aiofiles.open(history_path, mode='a') as history_file:
        msg = await queue.get()
        await history_file.write(msg)
        await history_file.flush()


async def read_msgs(
    r_reader, history_path, messages_queue, messages_history_queue,
    status_updates_queue, watchdog_queue
):
    while True:
        try:
            async with async_timeout.timeout(1) as cm:
                chat_message = await read_from_socket(r_reader)
            set_both_statuses(status_updates_queue, 'ESTABLISHED')
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
                await save_message(history_path, messages_history_queue)
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
        logger.error('File with token was not found')
    return token


async def login(w_reader, w_writer, status_updates_queue, watchdog_queue):
    await read_from_socket(w_reader)
    watchdog_queue.put_nowait('Connection is alive. Prompt before auth')
    status_updates_queue.put_nowait(
        gui.SendingConnectionStateChanged.ESTABLISHED)

    token = await process_token()
    try:
        await write_to_socket(w_writer, [token, '\n'])
    except MessageFormatError:
        exit_on_token_error()
    
    answer = None
    while not answer or answer == "\n":
        answer = await read_from_socket(w_reader)

    try:
        answer = answer.split('\n')[0]
        answer = json.loads(answer)
        if not answer:
            exit_on_token_error()
    except Exception as e:
        logger.error(f'Error loading token: {str(e)}')
        raise SystemExit

    logger.debug(
        f'Authorization complete. User {answer["nickname"]}.')
    event = gui.NicknameReceived(answer["nickname"])
    status_updates_queue.put_nowait(event)
    watchdog_queue.put_nowait('Connection is alive. Authorization done')


async def watch_for_connection(watchdog_queue):
    while True:
        message = await watchdog_queue.get()
        watchdog_logger.info(f'[{time.time()}] {message}')


def parse_args():
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
    return parser.parse_args()


async def main():
    
    args = parse_args()

    logging.basicConfig(
        format=(
            '%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s] '
            '%(message)s'
        ),
        level=logging.DEBUG
    )

    messages_queue = asyncio.Queue()
    messages_history_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()
    watchdog_queue = asyncio.Queue()

    set_both_statuses(status_updates_queue, 'INITIATED')

    try:
        async with create_task_group() as tg:
            tg.start_soon(watch_for_connection, watchdog_queue)

            tg.start_soon(gui.draw, messages_queue, sending_queue,
                status_updates_queue)

            tg.start_soon(handle_connection, args.host, args.port,
                args.writer_port, args.history, messages_queue,
                messages_history_queue, status_updates_queue, watchdog_queue,
                sending_queue)

    except gui.TkAppClosed:
        logger.info("Exit the app")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Exit the app with CTRL+C")
