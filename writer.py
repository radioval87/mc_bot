import asyncio
import json
import logging

import configargparse


async def read_and_save_to_log(reader):
    msg = await reader.read(1000)
    logging.debug(msg.decode())
    return msg


async def submit_message(host, port, token, message):
    reader, writer = await asyncio.open_connection(host, port)

    await read_and_save_to_log(reader)

    if not token:
        try:
            with open('.token', mode='r') as f:
                token = f.read()
        except Exception as e:
            logging.warning(f'Токен не найден. {str(e)}')

    token = f'{token}\n'
    writer.write(token.encode())

    answer = await read_and_save_to_log(reader)
    answer = answer.decode().split('\n')[0]
    
    try:
        if json.loads(answer) is None:
            logging.warning('Неизвестный токен. ' 
                            'Проверьте его или зарегистрируйте заново.')
            raise SystemExit
    except Exception as e:
        logging.error(f'Ошибка загрузки токена: {str(e)}')
    
    while True:
        if not message:
            message = input()
        writer.write(message.encode())
        writer.write('\n'.encode())
        writer.write('\n'.encode())
        message = None
        logging.debug(f'Sent message: {message}')


if __name__ == '__main__':
    parser = configargparse.ArgParser()
    parser.add_argument(
        '--host', type=str, help='Host address',
        env_var='WRITER_HOST', default='minechat.dvmn.org'
    )
    parser.add_argument(
        '--port', type=int, help=('Host port'), env_var='WRITER_PORT', default=5050
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
