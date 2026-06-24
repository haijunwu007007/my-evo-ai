import sys, os
sys.path.insert(0, '/home/ubuntu/my-evo-ai')
try:
    from api.routes.routes_ocr import router
    print('OK routes_ocr: prefix=' + router.prefix + ' routes=' + str(len(router.routes)))
except Exception as e:
    print('ERR routes_ocr: ' + str(e)[:200])

try:
    from modules.ocr_engine import recognize_image
    print('OK ocr_engine: has recognize_image=' + str(callable(recognize_image)))
except Exception as e:
    print('ERR ocr_engine import: ' + str(e)[:200])
    # Try just importing the module
    try:
        import modules.ocr_engine
        print('Module loaded, has recognize_image=' + str(hasattr(modules.ocr_engine, 'recognize_image')))
    except Exception as e2:
        print('ERR module import: ' + str(e2)[:200])
