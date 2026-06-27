import vosk, os, sys, traceback
try:
    d = os.path.expanduser('~\\vosk_models\\vosk-model-small-cn-0.22')
    print("model dir:", d)
    print("exists:", os.path.isdir(d))
    if os.path.isdir(d):
        print("contents:", os.listdir(d)[:5])
    m = vosk.Model(d)
    print("Vosk OK:", m)
except:
    traceback.print_exc()
    input("press enter")
