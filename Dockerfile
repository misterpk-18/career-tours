FROM public.ecr.aws/lambda/python:3.12

WORKDIR ${LAMBDA_TASK_ROOT}

COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY backend/ .

CMD ["app.handler"]