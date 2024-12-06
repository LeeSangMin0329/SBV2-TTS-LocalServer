import asyncio
import threading
from queue import Queue
from io import BytesIO
from scipy.io import wavfile
from flask import Flask, request, jsonify, send_file
from model_loader import voice
from model_settings import MODEL_NAME, ENCORDING_TYPE
from server_settings import LOCAL_HOST, SERVER_PORT_NUMBER, HTTPStatus

app = Flask(__name__)

# TODO: 태스크 결과 풀링하게 바꿀 것. 지금은 무한정 쌓임
tasks = {}
task_queue = Queue()

async def process_voice_request(task_id, message):
    try:
        sample_rate, audio = await voice(message, ENCORDING_TYPE, MODEL_NAME, 0, MODEL_NAME, 0)

        audio_buffer = BytesIO()
        wavfile.write(audio_buffer, sample_rate, audio)
        audio_buffer.seek(0)
        
        # 생성 완료 상태 업데이트
        tasks[task_id] = {'status': 'completed', 'file': audio_buffer}
    except Exception as e:
        tasks[task_id] = {'status': 'failed', 'error': str(e)}
    
def worker():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    while True:
        task_id, message = task_queue.get()

        if task_id is None:
            break

        loop.run_until_complete(process_voice_request(task_id, message))

@app.route('/generate_audio', methods=['POST'])
def generate_audio():
    message = request.form['message']

    if not message:
        return "No message provided", HTTPStatus.NO_MESSAGE

    print(f"Target message : {str(message)}")

    task_id = str(len(tasks) + 1)  # 고유한 작업 ID 생성
    tasks[task_id] = {'status': 'in_progress'}

    # 큐에 작업 넣기
    task_queue.put((task_id, message))

    return jsonify({'task_id': task_id, 'status': 'in_progress'}), HTTPStatus.IN_PROGRESS

@app.route('/download_audio', methods=['GET'])
def download_audio():
    task_id = request.args.get('task_id')

    task = tasks.get(task_id)
    if not task:
        return "Task not found", HTTPStatus.NOT_FOUND
    
    if task['status'] == 'completed':
        return send_file(task['file'], mimetype='audio/wav', as_attachment=True, download_name='output.wav')
    
    if task['status'] == 'in_progress':
        return jsonify({'status': 'in progress'}), HTTPStatus.IN_PROGRESS
    
    return jsonify({'status': 'failed', 'error': task.get('error', 'Unknown error')}), HTTPStatus.UNKNOWN_ERROR

if __name__ == '__main__':
    # 작업 큐와 작업자를 위한 별도 스레드
    threading.Thread(target=worker, daemon=True).start()
    app.run(host=LOCAL_HOST, port=SERVER_PORT_NUMBER)