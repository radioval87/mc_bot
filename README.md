This is a service for interaction with a TCP-based chat.

To start working with it, firstly you need to clone it to your machine, create a virtual environment using

`python3 -m venv venv`

activate this environment using

`source venv/bin/activate`

and install dependencies using

`pip3 install -r requirements.txt`

The service consists of three components:

1) To register a new chat user run `python3 register.py`
You can set the chat's address using `--host` argument or by setting a `REG_HOST` environment variable
You can set the chat's port using `--port` argument or by setting a `REG_PORT` environment variable

2) To see the chat run `python3 main.py`
You can set the chat's address using `--host` argument or by setting a `MAIN_HOST` environment variable
You can set the chat's port using `--port` argument or by setting a `MAIN_PORT` environment variable
You can set a path for a chat's history using `--history` argument or by setting a `HISTORY_PATH` environment variable

3) To log in and send a message to the chat use `python3 writer.py`
You must specify the first message that will be sent on connecting to the chat using `--message` argument
You can set the chat's address using `--host` argument or by setting a `WRITER_HOST` environment variable
You can set the chat's port using `--port` argument or by setting a `WRITER_PORT` environment variable
You can set the user's token using `--token` argument or by setting a `TOKEN` environment variable