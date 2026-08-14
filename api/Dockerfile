FROM public.ecr.aws/lambda/python:3.13

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ${LAMBDA_TASK_ROOT}/

RUN uv export --frozen --no-dev --no-emit-project --output-file /tmp/requirements.txt \
    && UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy uv pip install --system -r /tmp/requirements.txt

COPY . ${LAMBDA_TASK_ROOT}/


CMD [ "handler.lambda_handler" ]
