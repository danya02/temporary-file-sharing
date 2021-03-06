FROM python:3.9

COPY requirements.txt /
RUN pip3 install -r /requirements.txt


RUN wget -O /bootstrap.min.css https://cdn.jsdelivr.net/npm/bootstrap@5.1.1/dist/css/bootstrap.min.css
RUN wget -O /bootstrap.js https://cdn.jsdelivr.net/npm/bootstrap@5.1.1/dist/js/bootstrap.bundle.min.js

ENV PYTHONUNBUFFERED yes

COPY static/ /static
COPY templates/ /templates
COPY database.py /
COPY main.py /


ENTRYPOINT ["gunicorn", "main:app", "-w", "2", "--threads", "2", "-b 0.0.0.0:8000", "-R"]

