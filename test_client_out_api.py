import time
from server_settings import LOCAL_HOST, CLIENT_PORT_NUMBER, HTTPStatus
from flask import Flask, request, jsonify
from test_client_app import request_audio_generation, try_play_audio

app = Flask(__name__)

@app.route('/requset_message_form_outside', methods=['POST'])
def request_message_form_outside():
    message = request.form['message']

    if not message:
        return jsonify({'status': 'failed', 'error': 'No message provided'}), HTTPStatus.NO_MESSAGE

    is_in_progress = True
    timeout = 10
    interval = 0.2
    request_audio_generation(message)

    while timeout > 0 and is_in_progress:
        timeout -= interval
        time.sleep(interval)

        is_in_progress = try_play_audio()

    return jsonify({'status': 'success'}), HTTPStatus.COMPLETED

if __name__ == '__main__':
    app.run(host=LOCAL_HOST, port=CLIENT_PORT_NUMBER)
