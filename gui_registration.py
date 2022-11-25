import asyncio
import json
import tkinter as tk
from enum import Enum
from tkinter.scrolledtext import ScrolledText

import aiofiles
from anyio import ExceptionGroup, create_task_group

from common import manage_socket, write_to_socket


class TkAppClosed(Exception):
    pass


class ReadConnectionStateChanged(Enum):
    INITIATED = 'устанавливаем соединение'
    ESTABLISHED = 'соединение установлено'
    CLOSED = 'соединение закрыто'

    def __str__(self):
        return str(self.value)


class SendingConnectionStateChanged(Enum):
    INITIATED = 'устанавливаем соединение'
    ESTABLISHED = 'соединение установлено'
    CLOSED = 'соединение закрыто'

    def __str__(self):
        return str(self.value)


class NicknameReceived:
    def __init__(self, nickname):
        self.nickname = nickname


def process_new_message(input_field, sending_queue):
    text = input_field.get()
    sending_queue.put_nowait(text)
    input_field.delete(0, tk.END)


async def send_to_server(sending_queue, host, port):
    while True:
        async with manage_socket(host, port) as (reader, writer):
            msg = await sending_queue.get()
            await write_to_socket(writer, [msg, '\n'])


async def update_tk(root_frame, interval=1 / 120):
    while True:
        try:
            root_frame.update()
        except tk.TclError:
            # if application has been destroyed/closed
            raise TkAppClosed()
        await asyncio.sleep(interval)


async def read_from_chat(reader):
    msg = await reader.read(1000)
    decoded_msg = msg.decode()
    print('DCD:', decoded_msg)
    return decoded_msg


async def register(msg, host, port):
    async with manage_socket(host, port) as (reader, writer):
        await read_from_chat(reader)
        await write_to_socket(writer, ['\n'])
        await read_from_chat(reader)

        while True:
            await write_to_socket(writer, [msg, '\n'])

            await read_from_chat(reader)
            await write_to_socket(writer, [msg, '\n'])
            answer = await read_from_chat(reader)
            answer = answer.split('\n')[0]

            try:
                answer = json.loads(answer)
                token = answer['account_hash']
                username = answer['nickname']

                async with aiofiles.open('.token', mode='w') as f:
                    await f.write(token)
                print(f'You are successfully registered as {username}')
            except Exception as e:
                raise e
            finally:
                break


async def update_conversation_history(panel, messages_queue, sending_queue, host, port):    
    panel['state'] = 'normal'
    if panel.index('end-1c') != '1.0':
        panel.insert('end', '\n')
    panel.insert('end', 'Welcome to chat registration. Please enter your username')
    panel.yview(tk.END)
    panel['state'] = 'disabled'

    while True: 
        msg = await sending_queue.get()
        print(msg)
        if msg:
            await register(msg, host, port)
        # async with manage_socket(host, port) as (reader, _):
        #     msg = await read_from_chat(reader)

        # if msg == '':
        #     pass
        # # msg = await messages_queue.get()
        # panel['state'] = 'normal'
        # if panel.index('end-1c') != '1.0':
        #     panel.insert('end', '\n')
        # panel.insert('end', msg)
        # panel.yview(tk.END)
        # panel['state'] = 'disabled'
        




async def draw():
    sending_queue = asyncio.Queue()
    messages_queue = asyncio.Queue()

    root = tk.Tk()

    root.title('Чат Майнкрафтера')

    root_frame = tk.Frame()
    root_frame.pack(fill="both", expand=True)

    # status_labels = create_status_panel(root_frame)

    input_frame = tk.Frame(root_frame)
    input_frame.pack(side="bottom", fill=tk.X)

    input_field = tk.Entry(input_frame)
    input_field.pack(side="left", fill=tk.X, expand=True)

    input_field.bind("<Return>", lambda event: process_new_message(input_field, sending_queue))

    send_button = tk.Button(input_frame)
    send_button["text"] = "Отправить"
    send_button["command"] = lambda: process_new_message(input_field, sending_queue)
    send_button.pack(side="left")

    conversation_panel = ScrolledText(root_frame, wrap='none')
    conversation_panel.pack(side="top", fill="both", expand=True)
    
    host = 'minechat.dvmn.org'
    port = 5050
    try:
        async with create_task_group() as tg:
            tg.start_soon(update_tk, root_frame)
            tg.start_soon(update_conversation_history, conversation_panel, messages_queue, sending_queue, host, port)
            # tg.start_soon(send_to_server, sending_queue, host, port)
            
            # tg.start_soon(update_status_panel, status_labels, status_updates_queue)
    except ExceptionGroup:
        pass


if __name__ == '__main__':
    try:
        asyncio.run(draw())
    except KeyboardInterrupt:
        pass
