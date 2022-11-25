import asyncio
import json
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

import aiofiles
from anyio import create_task_group

from common import manage_socket, write_to_socket


class TkAppClosed(Exception):
    pass


def process_new_message(input_field, sending_queue):
    text = input_field.get()
    sending_queue.put_nowait(text)
    input_field.delete(0, tk.END)


async def update_tk(root_frame, interval=1 / 120):
    while True:
        try:
            root_frame.update()
        except tk.TclError:
            # if application has been destroyed/closed
            raise TkAppClosed()
        await asyncio.sleep(interval)


async def update_conversation_history(panel, messages_queue):
    while True:
        msg = await messages_queue.get()

        panel['state'] = 'normal'
        if panel.index('end-1c') != '1.0':
            panel.insert('end', '\n')
        panel.insert('end', msg)
        panel.yview(tk.END)
        panel['state'] = 'disabled'


async def read_from_chat(reader):
    msg = await reader.read(1000)
    decoded_msg = msg.decode()
    return decoded_msg


async def receive_token(messages_queue, chosen_username, host, port):
    async with manage_socket(host, port) as (reader, writer):
        await read_from_chat(reader)
        await write_to_socket(writer, ['\n'])
        await read_from_chat(reader)
        await read_from_chat(reader)
        await write_to_socket(writer, [chosen_username, '\n', '\n'])
        answer = await read_from_chat(reader)
        answer = answer.split('\n')[0]

        try:
            answer = json.loads(answer)
            token = answer['account_hash']
            username = answer['nickname']

            async with aiofiles.open('.token', mode='w') as f:
                await f.write(token)
            return username
        except json.decoder.JSONDecodeError:
            messages_queue.put_nowait(
                'Registration error. Please enter your username again')
            return


async def register(messages_queue, sending_queue, host, port):
    messages_queue.put_nowait(
        'Welcome to chat registration. Please enter your username')

    username = None    
    while not username:
        chosen_username = await sending_queue.get()
        if chosen_username:
            username = await receive_token(messages_queue, chosen_username,
                                           host, port)
    
    messages_queue.put_nowait(
        f'Congratulations! You are successfully registered as {username}')
    for t in range(5, 0, -1):
        messages_queue.put_nowait(f'Exiting in {t}...')
        await asyncio.sleep(1)
    raise TkAppClosed
            
    
async def draw():
    sending_queue = asyncio.Queue()
    messages_queue = asyncio.Queue()

    root = tk.Tk()

    root.title('Chat: Registration')

    root_frame = tk.Frame()
    root_frame.pack(fill="both", expand=True)

    input_frame = tk.Frame(root_frame)
    input_frame.pack(side="bottom", fill=tk.X)

    input_field = tk.Entry(input_frame)
    input_field.pack(side="left", fill=tk.X, expand=True)

    input_field.bind(
        "<Return>",
        lambda event: process_new_message(input_field, sending_queue)
    )

    send_button = tk.Button(input_frame)
    send_button["text"] = "Send"
    send_button["command"] = lambda: process_new_message(input_field,
                                                         sending_queue)
    send_button.pack(side="left")

    conversation_panel = ScrolledText(root_frame, wrap='none')
    conversation_panel.pack(side="top", fill="both", expand=True)
    
    host = 'minechat.dvmn.org'
    port = 5050
    try:
        async with create_task_group() as tg:
            tg.start_soon(update_tk, root_frame)
            tg.start_soon(register, messages_queue, sending_queue,
                          host, port)
            tg.start_soon(update_conversation_history, conversation_panel,
                          messages_queue)
    except TkAppClosed:
        print("Exit the app")           


if __name__ == '__main__':
    try:
        asyncio.run(draw())
    except KeyboardInterrupt:
        print("Exit the app with CTRL+C")
