from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/echo")
def echo(data: dict):
    return {"you_sent": data}
