import asyncio
import time
from enum import Enum
from io import BytesIO
from scipy.io import wavfile
from queue import Queue
from model_loader import voice
from model_settings import MODEL_NAME, SPEAKER_NAME, ENCORDING_TYPE

class ProcessStatus(int, Enum):
    COMPLETED = 200
    IN_PROGRESS = 202
    ERROR = 500

request_queue = Queue()
processes_dict = {}
MAX_QUEUE_SIZE = 20

next_task_id = 0
processed_task_id = 0

def run_worker():
    asyncio.run(worker())

def add_convert_request(message: str, face: str, animation: str, log_user: str, log_answer: str):
    global next_task_id

    if len(processes_dict) >= MAX_QUEUE_SIZE:
        print(f"converter result queue size is over. last task id: {next_task_id}")
        return str(next_task_id)

    next_task_id += 1

    id = str(next_task_id)
    processes_dict[id] = {'status': 'in_progress'}
    request_queue.put((id, message, face, animation, log_user, log_answer))
    return id


def get_convert_result() -> tuple[ProcessStatus, str, str, str, str, str, BytesIO]:
    global processed_task_id

    if not processes_dict:
        return ('error', None, None, None, None, None, None)
    
    task_id = max(processes_dict.keys(), key=int)

    # 진행된 결과가 없음.
    if processed_task_id >= int(task_id):
        return (ProcessStatus.IN_PROGRESS, None, None, None, None, None, None)

    convert_result = processes_dict.get(task_id)

    if not convert_result:
        return ('error', None, None, None, None, None, None)
    
    if convert_result['status'] == 'in_progress':
        return (ProcessStatus.IN_PROGRESS, None, None, None, None, None, None)
    
    elif convert_result['status'] == 'completed':
        message = convert_result['message']
        face = convert_result['face']
        animation = convert_result['anim']
        log_user = convert_result['log_user']
        log_answer = convert_result['log_answer']
        audio_buffer = convert_result['file']
        del processes_dict[task_id]

        processed_task_id = int(task_id)
        return ProcessStatus.COMPLETED, message, face, animation, log_user, log_answer, audio_buffer
    
    del processes_dict[task_id] # failed
    print(convert_result['error'])
    return (ProcessStatus.ERROR, None, None, None, None, None, None)


async def process_voice_request(task_id: str, message: str, face: str, animation: str, log_user: str, log_answer: str):
    try:
        start = time.time()
        
        sample_rate, audio = await voice(message, ENCORDING_TYPE, MODEL_NAME, 0, SPEAKER_NAME, 0)

        audio_buffer = BytesIO()
        wavfile.write(audio_buffer, sample_rate, audio)
        audio_buffer.seek(0)
        
        end = time.time()
        print(f"convert time: {end - start}")

        # 생성 완료 상태 업데이트
        processes_dict[task_id] = {'status': 'completed', 'message': message, 'face': face, 'anim': animation, 'file': audio_buffer, 'log_user': log_user, 'log_answer': log_answer}
    except Exception as e:
        processes_dict[task_id] = {'status': 'failed', 'error': str(e)}
    
def process_task_async(task_id, message, face, animation, log_user, log_answer):
    asyncio.create_task(process_voice_request(task_id, message, face, animation, log_user, log_answer))

async def worker():
    while True:
      
        if not request_queue.empty():
            task_id, message, face, animation, log_user, log_answer = request_queue.get()
            process_task_async(task_id, message, face, animation, log_user, log_answer)
        
        await asyncio.sleep(0.05)


