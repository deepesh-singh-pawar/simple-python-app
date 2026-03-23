import logging
import os

from ddtrace import patch_all
from ddtrace import tracer
from flask import Flask
from flask import request


patch_all(flask=True)

DD_SERVICE = os.getenv("DD_SERVICE", "simple-python-app")
DD_ENV = os.getenv("DD_ENV", "dev")
DD_VERSION = os.getenv("DD_VERSION", "1.0.0")
DD_LOG_LEVEL = os.getenv("DD_LOG_LEVEL", "INFO").upper()

tracer.set_tags(
    {
        "service": DD_SERVICE,
        "env": DD_ENV,
        "version": DD_VERSION,
    }
)

app = Flask(__name__)
app.logger.setLevel(getattr(logging, DD_LOG_LEVEL, logging.INFO))
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s "
        "service=%(dd_service)s env=%(dd_env)s version=%(dd_version)s "
        "trace_id=%(dd_trace_id)s span_id=%(dd_span_id)s "
        'message="%(message)s"'
    )
)
app.logger.handlers = [handler]


class DatadogContextFilter(logging.Filter):
    """Inject Datadog correlation fields into every log record."""

    def filter(self, record):
        span = tracer.current_span()
        record.dd_service = DD_SERVICE
        record.dd_env = DD_ENV
        record.dd_version = DD_VERSION
        record.dd_trace_id = str(span.trace_id if span else 0)
        record.dd_span_id = str(span.span_id if span else 0)
        return True


app.logger.addFilter(DatadogContextFilter())


@app.before_request
def log_request_start():
    app.logger.info("request started method=%s path=%s", request.method, request.path)


@app.after_request
def log_request_end(response):
    app.logger.info(
        "request completed method=%s path=%s status=%s",
        request.method,
        request.path,
        response.status_code,
    )
    return response


@app.route("/")
def home():
    app.logger.info("home endpoint called")
    return "Hello DevOps Engineer. Your app is running successfully!"


@app.route("/health")
def health():
    app.logger.info("health endpoint called")
    return {"status": "healthy"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
