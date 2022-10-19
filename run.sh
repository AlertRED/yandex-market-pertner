#!/bin/bash
kill -9 $(lsof -t -i:8000)
nohup python -m uvicorn main:app --port=8000 &
