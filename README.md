# TCP chat

This is a service for interaction with a TCP-based chat. It's available with UI or in the console


## Requirements

Python3 should be already installed.  
To start working with the service, firstly you need to: 

1. Clone it to your machine
2. Create a virtual environment using

```bash 
python3 -m venv venv
```

3. Activate this environment using

```bash
source venv/bin/activate
```
4. Install dependencies using

```bash
pip3 install -r requirements.txt
```

## Run

### UI version

The service consists of two components:

1. To register a new chat user run 
```bash
python3 register_gui.py
```

2. To login to chat as a registered user run 
```bash
python3 main_gui.py
```  
You can set the chat's address using `--host` argument or by setting a `MAIN_HOST` environment variable  
You can set the chat's port for receiveing messages using `--port` argument or by setting a `MAIN_PORT` environment variable  
You can set a path for a chat's history using `--history` argument or by setting a `HISTORY_PATH` environment variable
You can set the chat's port for sending messages using `--port` argument or by setting a `WRITER_PORT` environment variable  


### Console version

The service consists of three components:

1. To register a new chat user run 
```bash
python3 register.py
```
You can set the chat's address using `--host` argument or by setting a `REG_HOST` environment variable  
You can set the chat's port using `--port` argument or by setting a `REG_PORT` environment variable

2. To see the chat run 
```bash
python3 main.py
```  
You can set the chat's address using `--host` argument or by setting a `MAIN_HOST` environment variable  
You can set the chat's port using `--port` argument or by setting a `MAIN_PORT` environment variable  
You can set a path for a chat's history using `--history` argument or by setting a `HISTORY_PATH` environment variable

3. To log in and send a message to the chat use 
```bash
python3 writer.py
```
You must specify the message that will be sent to the chat using `--message` argument  
You can set the chat's address using `--host` argument or by setting a `WRITER_HOST` environment variable  
You can set the chat's port using `--port` argument or by setting a `WRITER_PORT` environment variable  
You can set the user's token using `--token` argument or by setting a `TOKEN` environment variable
