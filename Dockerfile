FROM python:latest

RUN apt-get update && apt-get install -y git

RUN pip install PyGithub black gitpython isort

WORKDIR /bot

COPY . ./

CMD ["python", "service.py"]