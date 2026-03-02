FROM python:3.13-alpine
COPY deye_power_limit.py /app/
WORKDIR /app
ENTRYPOINT ["python", "deye_power_limit.py"]
