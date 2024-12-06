import requests
import time
from server_settings import LOCAL_HOST, SERVER_PORT_NUMBER, HTTPStatus

import simpleaudio as sa

# 서버 주소 (로컬)
server_url = f"http://{LOCAL_HOST}:{SERVER_PORT_NUMBER}"

task_id = 0

# 생성 요청을 보내는 함수
def request_audio_generation(message):
    global task_id

    response = requests.post(f"{server_url}/generate_audio", data={"message": message})
    
    if response.status_code == HTTPStatus.NO_MESSAGE:
        print("Error: No Message")
        return

    response_json = response.json()

    task_id = response_json["task_id"]

    if response.status_code == HTTPStatus.IN_PROGRESS:
        print(f"task id {task_id} : Audio generation request received, waiting for file...")
    else:
        print(f"Error: {response.status_code}, {response.text}")

# 다운로드 요청을 보내는 함수
def download_audio():
    global task_id
    print("Waiting for the audio file to be ready...")

    # 파일 다운로드 URL (생성된 파일을 가져오는 URL)
    download_url = f"{server_url}/download_audio"
    
    # 다운로드 요청
    response = requests.get(download_url, stream=True, params={"task_id": task_id})

    if response.status_code == HTTPStatus.COMPLETED:
        with open(f"test_data/output{task_id}.wav", "wb") as f:
            f.write(response.content)
        print("Audio file downloaded successfully.")

    else:
        print(f"Error: {response.status_code}, {response.text}")

def try_play_audio():
    global task_id
    print("Waiting for the audio file to be ready...")

    # 파일 다운로드 URL (생성된 파일을 가져오는 URL)
    download_url = f"{server_url}/download_audio"

    # 다운로드 요청
    response = requests.get(download_url, stream=True, params={"task_id": task_id})

    if response.status_code == HTTPStatus.COMPLETED:
        sa.play_buffer(response.content, num_channels=1, bytes_per_sample=2, sample_rate=44100)
        print("Audio file downloaded successfully.")
        return False
    
    elif response.status_code == HTTPStatus.IN_PROGRESS:
        return True
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return False


def main():
    while True:
        message = input("Enter message: ")
        request_audio_generation(message)

        if message is None:
            continue

        sa.stop_all()

        is_in_progress = True
        while is_in_progress:
            time.sleep(0.2)
            is_in_progress = try_play_audio()
            


# 클라이언트가 생성 요청을 보내고, 다운로드 요청을 기다리는 흐름
if __name__ == "__main__":
    main()