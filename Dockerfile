FROM public.ecr.aws/lambda/python:3.12

WORKDIR ${LAMBDA_TASK_ROOT}

COPY requirements.txt .

# --no-cache-dir matters here: without it pip leaves its wheel cache in the
# layer, which was 66MB of an image nothing ever reads. The separate
# `pip install --upgrade pip` this replaces only added a layer — pip is already
# present in the base image and its version is irrelevant to the runtime.
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

CMD ["app.handler"]