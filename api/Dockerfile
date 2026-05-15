FROM python:3.12-slim

RUN adduser --disabled-password --gecos '' api-user

WORKDIR /opt/siniestralidad-api

COPY . /opt/siniestralidad-api/
RUN pip install --upgrade pip && pip install -r requirements.txt

RUN chown -R api-user:api-user ./

USER api-user

EXPOSE 8000

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
