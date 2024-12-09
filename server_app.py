import threading
from flask import Flask, request, jsonify, send_file
from server_settings import LOCAL_HOST, SERVER_PORT_NUMBER, HTTPStatus
from tts_converter import run_worker, add_convert_request, get_convert_result, ProcessStatus

app = Flask(__name__)

@app.route('/generate_audio', methods=['POST'])
def generate_audio():
    message = request.form['message']

    if not message:
        return "No message provided", HTTPStatus.NO_MESSAGE

    print(f"Target message : {str(message)}")

    task_id = add_convert_request(message)

    return jsonify({'task_id': task_id, 'status': 'in_progress'}), HTTPStatus.IN_PROGRESS

@app.route('/download_audio', methods=['GET'])
def download_audio():
    task_id = request.args.get('task_id')

    status, _, audio_buffer = get_convert_result(task_id)

    if status == ProcessStatus.ERROR:
        return "Task not found", HTTPStatus.NOT_FOUND
    
    if status == ProcessStatus.COMPLETED:
        return send_file(audio_buffer, mimetype='audio/wav', as_attachment=True, download_name='output.wav'), HTTPStatus.COMPLETED
    
    if status == ProcessStatus.IN_PROGRESS:
        return jsonify({'status': 'in progress'}), HTTPStatus.IN_PROGRESS
    
    return jsonify({'status': 'failed', 'error': 'Unknown error'}), HTTPStatus.UNKNOWN_ERROR

@app.route('/get_text_message', methods=['GET'])
def get_text_message():
    task_id = request.args.get('task_id')

    status, message, _ = get_convert_result(task_id)

    if status == ProcessStatus.ERROR:
        return "Task not found", HTTPStatus.NOT_FOUND
    
    if status == ProcessStatus.COMPLETED:
        return jsonify({'status': 'completed', 'message': message})
    
    if status == ProcessStatus.IN_PROGRESS:
        return jsonify({'status': 'in progress'}), HTTPStatus.IN_PROGRESS
    
    return jsonify({'status': 'failed', 'error': 'Unknown error'}), HTTPStatus.UNKNOWN_ERROR

if __name__ == '__main__':
    # 작업 큐와 작업자를 위한 별도 스레드
    threading.Thread(target=run_worker, daemon=True).start()
    app.run(host=LOCAL_HOST, port=SERVER_PORT_NUMBER)
