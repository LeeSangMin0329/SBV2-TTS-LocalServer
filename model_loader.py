import sys
from typing import Any, Optional
from urllib.parse import unquote

import GPUtil
import psutil
import torch
from numpy.typing import NDArray

from config import get_config
from style_bert_vits2.constants import (
    DEFAULT_ASSIST_TEXT_WEIGHT,
    DEFAULT_LENGTH,
    DEFAULT_LINE_SPLIT,
    DEFAULT_NOISE,
    DEFAULT_NOISEW,
    DEFAULT_SDP_RATIO,
    DEFAULT_SPLIT_INTERVAL,
    DEFAULT_STYLE,
    DEFAULT_STYLE_WEIGHT,
    Languages,
)
from style_bert_vits2.tts_model import TTSModel, TTSModelHolder
from style_bert_vits2.logging import logger
from style_bert_vits2.nlp import bert_models
from style_bert_vits2.nlp.japanese import pyopenjtalk_worker as pyopenjtalk
from style_bert_vits2.nlp.japanese.user_dict import update_dict
from style_bert_vits2.tts_model import TTSModel, TTSModelHolder
from model_settings import (
    DEVICE,
    MODEL_DIR,
)

config = get_config()

# pyopenjtalk_worker を起動
## pyopenjtalk_worker は TCP ソケットサーバーのため、ここで起動する
pyopenjtalk.initialize_worker()

# dict_data/ 以下の辞書データを pyopenjtalk に適用
update_dict()

# 事前に BERT モデル/トークナイザーをロードしておく
## ここでロードしなくても必要になった際に自動ロードされるが、時間がかかるため事前にロードしておいた方が体験が良い
bert_models.load_model(Languages.JP)
bert_models.load_tokenizer(Languages.JP)
# bert_models.load_model(Languages.EN)
# bert_models.load_tokenizer(Languages.EN)
# bert_models.load_model(Languages.ZH)
# bert_models.load_tokenizer(Languages.ZH)

def raise_validation_error(msg: str, param: str):
    logger.warning(f"Validation error: {msg}")
    raise Exception(
        status_code=422,
        detail=[dict(type="invalid_params", msg=msg, loc=["query", param])],
    )

def load_models(model_holder: TTSModelHolder):
    global loaded_models
    global mpath
    loaded_models = []
    for model_name, model_paths in model_holder.model_files_dict.items():
        model = TTSModel(
            model_path=model_paths[0],
            config_path=model_holder.root_dir / model_name / "config.json",
            style_vec_path=model_holder.root_dir / model_name / "style_vectors.npy",
            device=model_holder.device,
        )
        mpath = model_paths[0]
        # 起動時に全てのモデルを読み込むのは時間がかかりメモリを食うのでやめる
        # model.load()
        loaded_models.append(model)

if (DEVICE == "cpu"):
    device = "cpu"
else:
    device = "cuda" if torch.cuda.is_available() else "cpu"

model_dir = MODEL_DIR
model_holder = TTSModelHolder(model_dir, device)
if len(model_holder.model_names) == 0:
    logger.error(f"Models not found in {model_dir}.")
    sys.exit(1)

logger.info("Loading models...")
load_models(model_holder)

limit = config.server_config.limit
if limit < 1:
    limit = None
else:
    logger.info(
        f"The maximum length of the text is {limit}. If you want to change it, modify config.yml. Set limit to -1 to remove the limit."
    )

async def voice(
    text: str = "セリフ",
    encoding: str = "utf-8",
    model_name: str = "model_assets", # "モデル名(model_idより優先)。model_assets内のディレクトリ名を指定"
    model_id: int = 0, # モデルID。`GET /models/info`のkeyの値を指定ください
    speaker_name: str = None, # "話者名(speaker_idより優先)。esd.listの2列目の文字列を指定"
    speaker_id: int = 0, # "話者ID。model_assets>[model]>config.json内のspk2idを確認"
    sdp_ratio: float = DEFAULT_SDP_RATIO, # "SDP(Stochastic Duration Predictor)/DP混合比。比率が高くなるほどトーンのばらつきが大きくなる"
    noise: float = DEFAULT_NOISE, # ="サンプルノイズの割合。大きくするほどランダム性が高まる"
    noisew: float = DEFAULT_NOISEW, # "SDPノイズ。大きくするほど発音の間隔にばらつきが出やすくなる"
    length: float = DEFAULT_LENGTH, # "話速。基準は1で大きくするほど音声は長くなり読み上げが遅まる"
    language: Languages = Languages.JP, # "textの言語"
    auto_split: bool = DEFAULT_LINE_SPLIT, # "改行で分けて生成"
    split_interval: float = DEFAULT_SPLIT_INTERVAL, # "分けた場合に挟む無音の長さ（秒）
    assist_text: Optional[str] = None, # "このテキストの読み上げと似た声音・感情になりやすくなる。ただし抑揚やテンポ等が犠牲になる傾向がある"
    assist_text_weight: float = DEFAULT_ASSIST_TEXT_WEIGHT, # "assist_textの強さ"
    style: Optional[str] = DEFAULT_STYLE, # "スタイル"
    style_weight: float = DEFAULT_STYLE_WEIGHT, # "スタイルの強さ"
    reference_audio_path: Optional[str] = None, # "スタイルを音声ファイルで行う"
) -> tuple[int, NDArray[Any]]:
    """Infer text to speech(テキストから感情付き音声を生成する)"""
    if model_id >= len(model_holder.model_names):  # /models/refresh があるためQuery(le)で表現不可
        raise_validation_error(f"model_id={model_id} not found", "model_id")

    if model_name:
        # load_models() の 処理内容が i の正当性を担保していることに注意
        model_ids = [i for i, x in enumerate(model_holder.models_info) if x.name == model_name]
        if not model_ids:
            raise_validation_error(
                f"model_name={model_name} not found", "model_name"
            )
        # 今の実装ではディレクトリ名が重複することは無いはずだが...
        if len(model_ids) > 1:
            raise_validation_error(
                f"model_name={model_name} is ambiguous", "model_name"
            )
        model_id = model_ids[0]
        
    model = loaded_models[model_id]
    if speaker_name is None:
        if speaker_id not in model.id2spk.keys():
            raise_validation_error(
                f"speaker_id={speaker_id} not found", "speaker_id"
            )
    else:
        if speaker_name not in model.spk2id.keys():
            raise_validation_error(
                f"speaker_name={speaker_name} not found", "speaker_name"
            )
        speaker_id = model.spk2id[speaker_name]
    if style not in model.style2id.keys():
        raise_validation_error(f"style={style} not found", "style")
    assert style is not None
    if encoding is not None:
        text = unquote(text, encoding=encoding)
    sr, audio = model.infer(
        text=text,
        language=language,
        speaker_id=speaker_id,
        reference_audio_path=reference_audio_path,
        sdp_ratio=sdp_ratio,
        noise=noise,
        noise_w=noisew,
        length=length,
        line_split=auto_split,
        split_interval=split_interval,
        assist_text=assist_text,
        assist_text_weight=assist_text_weight,
        use_assist_text=bool(assist_text),
        style=style,
        style_weight=style_weight,
    )
    logger.success("Audio data generated and sent successfully")
    return sr, audio

def get_loaded_models_info():
    """ロードされたモデル情報の取得"""

    result: dict[str, dict[str, Any]] = dict()
    for model_id, model in enumerate(loaded_models):
        result[str(model_id)] = {
            "config_path": model.config_path,
            "model_path": model.model_path,
            "device": model.device,
            "spk2id": model.spk2id,
            "id2spk": model.id2spk,
            "style2id": model.style2id,
        }
    return result

def refresh():
    """モデルをパスに追加/削除した際などに読み込ませる"""
    model_holder.refresh()
    load_models(model_holder)
    return get_loaded_models_info()

def get_status():
    """実行環境のステータスを取得"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory_info = psutil.virtual_memory()
    memory_total = memory_info.total
    memory_available = memory_info.available
    memory_used = memory_info.used
    memory_percent = memory_info.percent
    gpuInfo = []
    devices = ["cpu"]
    for i in range(torch.cuda.device_count()):
        devices.append(f"cuda:{i}")
    gpus = GPUtil.getGPUs()
    for gpu in gpus:
        gpuInfo.append(
            {
                "gpu_id": gpu.id,
                "gpu_load": gpu.load,
                "gpu_memory": {
                    "total": gpu.memoryTotal,
                    "used": gpu.memoryUsed,
                    "free": gpu.memoryFree,
                },
            }
        )
    return {
        "devices": devices,
        "cpu_percent": cpu_percent,
        "memory_total": memory_total,
        "memory_available": memory_available,
        "memory_used": memory_used,
        "memory_percent": memory_percent,
        "gpu": gpuInfo,
    }
