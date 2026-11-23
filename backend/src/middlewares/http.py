import logging
import time
import uuid

import psycopg
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


async def correlate(request, call_next):
    request_id = uuid.uuid4().hex
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers['X-Request-ID'] = request_id
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


async def observe(request, call_next):
    started = time.monotonic()
    response = await call_next(request)
    if response.status_code >= 500:
        logger.error('%s %s %s %.3fs', request.state.request_id, request.method, response.status_code,
                     time.monotonic() - started)
    response.headers['Cache-Control'] = 'no-store'
    return response


def install(app):
    app.middleware('http')(observe)
    app.middleware('http')(correlate)

    @app.exception_handler(RequestValidationError)
    async def invalid(request, error):
        issue = error.errors()[0]
        message = issue.get('ctx', {}).get('error')
        fields = ' / '.join(str(item) for item in issue['loc'][1:])
        return JSONResponse(status_code=422, content={'detail': str(message) if message else f'请核对输入字段 {fields}'})

    @app.exception_handler(psycopg.errors.UniqueViolation)
    async def duplicate(request, error):
        return JSONResponse(status_code=409, content={'detail': '编号或同月版本名称已存在'})

    @app.exception_handler(psycopg.OperationalError)
    async def unavailable(request, error):
        return JSONResponse(status_code=503, content={'detail': '数据库暂不可用，请稍后重试'})
