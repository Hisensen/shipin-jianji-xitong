"""Web UI 启动入口：python run.py"""
import os

import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8800"))
    uvicorn.run("app.web:app", host="127.0.0.1", port=port, reload=False)
