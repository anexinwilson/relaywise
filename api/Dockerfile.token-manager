FROM public.ecr.aws/lambda/python:3.13

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY . ${LAMBDA_TASK_ROOT}/

RUN UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy uv pip install --system -r requirements.txt

CMD [ "main.handler" ]