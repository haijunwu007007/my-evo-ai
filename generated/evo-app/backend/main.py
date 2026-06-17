from fastapi import FastAPI
app = FastAPI(title="evo-app")
@app.get("/")
def root():
    return {"ok": True}
