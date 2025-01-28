import threading
import json
import struct
from io import BytesIO
from flask import Flask, request, jsonify, send_file
from server_settings import LOCAL_HOST, SERVER_PORT_NUMBER, HTTPStatus
from tts_converter import run_worker, add_convert_request, get_convert_result, ProcessStatus

app = Flask(__name__)

@app.route('/generate_audio', methods=['POST'])
def generate_audio():
    message = request.form['message']
    face = request.form['face']
    animation = request.form['anim']
    log_user = request.form['log_user']
    log_answer = request.form['log_answer']

    if not message:
        return "No message provided", HTTPStatus.NO_MESSAGE

    print(f"Target message : {str(message)}")

    task_id = add_convert_request(message, face, animation, log_user, log_answer)

    return jsonify({'task_id': task_id, 'status': 'in_progress'}), HTTPStatus.IN_PROGRESS

@app.route('/download_audio', methods=['GET'])
def download_audio():
    status, message, face, animation, log_user, log_answer, audio_buffer = get_convert_result()

    if status == ProcessStatus.ERROR:
        return "Task not found", HTTPStatus.NOT_FOUND
    
    if status == ProcessStatus.COMPLETED:
        json_data = {'face': face, 'anim': animation, 'log_user': log_user, 'log_answer': log_answer}
        json_bytes = json.dumps(json_data).encode('utf-8')

        # 엔디안에 주의.
        json_size = struct.pack(">Q", len(json_bytes))

        response_data = BytesIO()
        response_data.write(json_size)
        response_data.write(json_bytes)
        response_data.write(audio_buffer.getvalue())
        response_data.seek(0)

        return send_file(response_data, mimetype='audio/wav', as_attachment=True, download_name='output.wav'), HTTPStatus.COMPLETED
    
    if status == ProcessStatus.IN_PROGRESS:
        return jsonify({'status': 'in progress'}), HTTPStatus.IN_PROGRESS
    
    return jsonify({'status': 'failed', 'error': 'Unknown error'}), HTTPStatus.UNKNOWN_ERROR

if __name__ == '__main__':
    # 작업 큐와 작업자를 위한 별도 스레드
    threading.Thread(target=run_worker, daemon=True).start()
    app.run(host=LOCAL_HOST, port=SERVER_PORT_NUMBER)
