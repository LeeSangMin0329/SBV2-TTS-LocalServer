import asyncio
from enum import Enum
from io import BytesIO
from scipy.io import wavfile
from queue import Queue
from model_loader import voice
from model_settings import MODEL_NAME, ENCORDING_TYPE

class ProcessStatus(int, Enum):
    COMPLETED = 200
    IN_PROGRESS = 202
    ERROR = 500

request_queue = Queue()
processes_dict = {}
MAX_QUEUE_SIZE = 20

next_task_id = 0

def run_worker():
    asyncio.run(worker())

def add_convert_request(message: str):
    global next_task_id

    if len(processes_dict) >= MAX_QUEUE_SIZE:
        print(f"converter result queue size is over. last task id: {next_task_id}")
        return str(next_task_id)

    next_task_id += 1

    id = str(next_task_id)
    processes_dict[id] = {'status': 'in_progress'}
    request_queue.put((id, message))
    return id


def get_convert_result(task_id) -> tuple[ProcessStatus, str, BytesIO]:
    convert_result = processes_dict.get(task_id)

    if not convert_result:
        return ('error', None, None)
    
    if convert_result['status'] == 'in_progress':
        return (ProcessStatus.IN_PROGRESS, None, None)
    
    elif convert_result['status'] == 'completed':
        message = convert_result['message']
        audio_buffer = convert_result['file']
        del processes_dict[task_id]

        return ProcessStatus.COMPLETED, message, audio_buffer
    
    del processes_dict[task_id] # failed
    print(convert_result['error'])
    return (ProcessStatus.ERROR, None, None)


async def process_voice_request(task_id: str, message):
    try:
        sample_rate, audio = await voice(message, ENCORDING_TYPE, MODEL_NAME, 0, MODEL_NAME, 0)

        audio_buffer = BytesIO()
        wavfile.write(audio_buffer, sample_rate, audio)
        audio_buffer.seek(0)
        
        # 생성 완료 상태 업데이트
        processes_dict[task_id] = {'status': 'completed', 'message': message, 'file': audio_buffer}
    except Exception as e:
        processes_dict[task_id] = {'status': 'failed', 'error': str(e)}
    
def process_task_async(task_id, message):
    asyncio.create_task(process_voice_request(task_id, message))

async def worker():
    while True:
      
        if not request_queue.empty():
            task_id, message = request_queue.get()
            process_task_async(task_id, message)
        
        await asyncio.sleep(0.05)


