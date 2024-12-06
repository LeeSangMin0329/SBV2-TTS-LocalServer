import json

import torch
from pathlib import Path
from config import get_path_config
from model_settings import BASE_DIR, MODEL_DIR, MODEL_NAME
from typing import Optional
import datetime
from style_bert_vits2.nlp.japanese.g2p_utils import g2kata_tone, kata_tone2phone_tone
from style_bert_vits2.models.infer import InvalidToneError
from style_bert_vits2.nlp.japanese.normalizer import normalize_text
from style_bert_vits2.tts_model import TTSModelHolder
from style_bert_vits2.nlp import bert_models
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
    GRADIO_THEME,
    Languages,
)
from style_bert_vits2.nlp.japanese import pyopenjtalk_worker
from style_bert_vits2.nlp.japanese.user_dict import update_dict

# pyopenjtalk_worker を起動
## pyopenjtalk_worker は TCP ソケットサーバーのため、ここで起動する
pyopenjtalk_worker.initialize_worker()
update_dict()
bert_models.load_model(Languages.JP)
bert_models.load_tokenizer(Languages.JP)
device = "cuda" if torch.cuda.is_available() else "cpu"

path_config = get_path_config()
model_holder = TTSModelHolder(Path(path_config.assets_root), device)

kataton = ""
def main():
    global kataton

    while True:
        input()

        message, (sr, audio), kataton = tts_fn(
            text="こんにちは、初めまして。あなたの名前はなんていうの？",
            model_name="Kaichou1", # "モデル名(model_idより優先)。model_assets内のディレクトリ名を指定"
            model_path= "model_assets/Kaichou1/Kaichou1_e100_s27800.safetensors", # MODEL_DIR / MODEL_NAME / "Kaichou1_e100_s27800.safetensors",
            speaker= "Kaichou1", # "話者名(speaker_idより優先)。esd.listの2列目の文字列を指定"
            sdp_ratio = DEFAULT_SDP_RATIO, # "SDP(Stochastic Duration Predictor)/DP混合比。比率が高くなるほどトーンのばらつきが大きくなる"
            noise_scale = DEFAULT_NOISE, # ="サンプルノイズの割合。大きくするほどランダム性が高まる"
            noise_scale_w = DEFAULT_NOISEW, # "SDPノイズ。大きくするほど発音の間隔にばらつきが出やすくなる"
            length_scale = DEFAULT_LENGTH, # "話速。基準は1で大きくするほど音声は長くなり読み上げが遅まる"
            language= Languages.JP, # "textの言語"
            line_split= DEFAULT_LINE_SPLIT, # "改行で分けて生成"
            split_interval=False, # "分けた場合に挟む無音の長さ（秒）
            assist_text= None, # "このテキストの読み上げと似た声音・感情になりやすくなる。ただし抑揚やテンポ等が犠牲になる傾向がある"
            assist_text_weight= DEFAULT_ASSIST_TEXT_WEIGHT, # "assist_textの強さ"
            style=DEFAULT_STYLE, # "スタイル"
            style_weight= DEFAULT_STYLE_WEIGHT, # "スタイルの強さ"
            reference_audio_path = None, # "スタイルを音声ファイルで行う"
            kata_tone_json_str = kataton,
            pitch_scale=1,
            intonation_scale=1,
            use_assist_text=False,
            use_tone=False
    )

def tts_fn(
        model_name,
        model_path,
        text,
        language,
        reference_audio_path,
        sdp_ratio,
        noise_scale,
        noise_scale_w,
        length_scale,
        line_split,
        split_interval,
        assist_text,
        assist_text_weight,
        use_assist_text,
        style,
        style_weight,
        kata_tone_json_str,
        use_tone,
        speaker,
        pitch_scale,
        intonation_scale,
    ):

        model_holder.get_model(model_name, str(model_path))
        assert model_holder.current_model is not None

        wrong_tone_message = ""
        kata_tone: Optional[list[tuple[str, int]]] = None
        if use_tone and kata_tone_json_str != "":
            if language != "JP":
                wrong_tone_message = "アクセント指定は現在日本語のみ対応しています。"
            if line_split:
                wrong_tone_message = (
                    "アクセント指定は改行で分けて生成を使わない場合のみ対応しています。"
                )
            try:
                kata_tone = []
                json_data = json.loads(kata_tone_json_str)
                # tupleを使うように変換
                for kana, tone in json_data:
                    assert isinstance(kana, str) and tone in (0, 1), f"{kana}, {tone}"
                    kata_tone.append((kana, tone))
            except Exception as e:
                wrong_tone_message = f"アクセント指定が不正です: {e}"
                kata_tone = None

        # toneは実際に音声合成に代入される際のみnot Noneになる
        tone: Optional[list[int]] = None
        if kata_tone is not None:
            phone_tone = kata_tone2phone_tone(kata_tone)
            tone = [t for _, t in phone_tone]

        speaker_id = model_holder.current_model.spk2id[speaker]
        breakpoint()
        start_time = datetime.datetime.now()

        try:
            sr, audio = model_holder.current_model.infer(
                text=text,
                language=language,
                reference_audio_path=reference_audio_path,
                sdp_ratio=sdp_ratio,
                noise=noise_scale,
                noise_w=noise_scale_w,
                length=length_scale,
                line_split=line_split,
                split_interval=split_interval,
                assist_text=assist_text,
                assist_text_weight=assist_text_weight,
                use_assist_text=use_assist_text,
                style=style,
                style_weight=style_weight,
                given_tone=tone,
                speaker_id=speaker_id,
                pitch_scale=pitch_scale,
                intonation_scale=intonation_scale,
            )
        except InvalidToneError as e:
            return f"Error: アクセント指定が不正です:\n{e}", None, kata_tone_json_str
        except ValueError as e:
            return f"Error: {e}", None, kata_tone_json_str

        end_time = datetime.datetime.now()
        duration = (end_time - start_time).total_seconds()

        print(str(duration))

        if tone is None and language == "JP":
            # アクセント指定に使えるようにアクセント情報を返す
            norm_text = normalize_text(text)
            kata_tone = g2kata_tone(norm_text)
            kata_tone_json_str = json.dumps(kata_tone, ensure_ascii=False)
        elif tone is None:
            kata_tone_json_str = ""
        message = f"Success, time: {duration} seconds."
        if wrong_tone_message != "":
            message = wrong_tone_message + "\n" + message
        return message, (sr, audio), kata_tone_json_str


main()