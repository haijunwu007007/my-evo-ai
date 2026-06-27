"""Vosk 子进程工作器 — 被 routes_speech.py 通过 subprocess 调用"""
import os, io, json, sys, wave, struct
VOSK_DIR = r"C:\vosk_model" if os.name == "nt" else "/home/ubuntu/vosk_models/vosk-model-small-cn-0.22"

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "no_wav_path"}))
        return
    wav_path = sys.argv[1]
    if not os.path.isfile(wav_path):
        print(json.dumps({"success": False, "error": "wav_not_found"}))
        return
    try:
        with open(wav_path, "rb") as f:
            raw = f.read()
        os.unlink(wav_path)
    except Exception as e:
        print(json.dumps({"success": False, "error": f"read_fail:{e}"}))
        return

    # Parse WAV
    if raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
        print(json.dumps({"success": False, "error": "not_wav"}))
        return

    try:
        with wave.open(io.BytesIO(raw), "rb") as wf:
            ch, sw, sr, nf = wf.getnchannels(), wf.getsampwidth(), wf.getframerate(), wf.getnframes()
            if sw == 2 and ch == 1 and sr == 16000:
                pcm = wf.readframes(nf)
            elif sw == 2 and ch > 1:
                frames = wf.readframes(nf)
                import array
                data = array.array('h', frames)
                pcm = bytes(data[0::ch])
            elif sw == 1:
                frames = wf.readframes(nf)
                import array
                data = array.array('B', frames)
                data16 = array.array('h', ((b - 128) << 8 for b in data))
                if ch > 1:
                    data16 = data16[0::ch]
                pcm = bytes(data16)
            else:
                # Resample via audioop
                frames = wf.readframes(nf)
                import audioop
                if sw == 2 and ch > 1:
                    frames = audioop.tomono(frames, sw, 0.5, 0.5)
                if sr != 16000:
                    frames, _ = audioop.ratecv(frames, sw, 1, sr, 16000, None)
                pcm = frames
    except Exception as e:
        print(json.dumps({"success": False, "error": f"wav_parse:{e}"}))
        return

    if not pcm or len(pcm) < 2000:
        print(json.dumps({"success": False, "error": "pcm_too_short"}))
        return

    try:
        import vosk
        model = vosk.Model(VOSK_DIR)
        rec = vosk.KaldiRecognizer(model, 16000)
        try:
            rec.SetWords(True)
        except Exception:
            pass

        CHUNK = 8000
        texts = []
        for i in range(0, len(pcm), CHUNK):
            chunk = pcm[i:i + CHUNK]
            if rec.AcceptWaveform(chunk):
                try:
                    r = json.loads(rec.Result())
                    t = r.get("text", "").strip()
                    if t:
                        texts.append(t)
                except Exception:
                    pass

        try:
            final = json.loads(rec.FinalResult())
            t = final.get("text", "").strip()
            if t:
                texts.append(t)
        except Exception:
            pass

        full = " ".join(texts).strip()
        if full:
            print(json.dumps({"success": True, "text": full}))
            return

        # Fallback
        rec2 = vosk.KaldiRecognizer(model, 16000)
        if rec2.AcceptWaveform(pcm):
            r = json.loads(rec2.Result())
            t = r.get("text", "").strip()
            if t:
                print(json.dumps({"success": True, "text": t}))
                return
        fr = json.loads(rec2.FinalResult())
        t = fr.get("text", "").strip()
        if t:
            print(json.dumps({"success": True, "text": t}))
            return

        print(json.dumps({"success": False, "error": "no_text"}))
    except Exception as e:
        print(json.dumps({"success": False, "error": f"vosk_err:{e}"}))

if __name__ == "__main__":
    main()
