import logging
import os
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from functools import wraps
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Callable, TypeVar

from ichatbio.agent_response import ResponseContext, IChatBioAgentProcess


# --- Configuration ---
class LogConfig:
    """Centralized logging configuration"""

    LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    LOG_FILE = os.path.join(LOG_DIR, "gbif_agent.log")
    LOG_TTL_DAYS = int(os.getenv("GBIF_LOG_TTL_DAYS", "5"))
    LOG_LEVEL = os.getenv("GBIF_LOG_LEVEL", "INFO").upper()
    LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s | %(message)s"
    DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
    MAX_LOG_SIZE = int(os.getenv("GBIF_MAX_LOG_SIZE", "10485760"))  # 10MB
    BACKUP_COUNT = int(os.getenv("GBIF_LOG_BACKUP_COUNT", "5"))


# --- Thread-safe logger setup ---
_logger_lock = threading.Lock()
_logger_instance: logging.Logger | None = None


def setup_logger() -> logging.Logger:
    """Setup logger with thread safety and error handling"""
    global _logger_instance

    if _logger_instance is not None:
        return _logger_instance

    with _logger_lock:
        try:
            Path(LogConfig.LOG_DIR).mkdir(parents=True, exist_ok=True)
            logger = logging.getLogger("gbif.agent")
            logger.setLevel(getattr(logging, LogConfig.LOG_LEVEL))
            logger.handlers.clear()
            handler = TimedRotatingFileHandler(
                LogConfig.LOG_FILE,
                when="midnight",
                interval=1,
                backupCount=LogConfig.LOG_TTL_DAYS,
                utc=True,
                encoding="utf-8",
            )
            formatter = logging.Formatter(
                fmt=LogConfig.LOG_FORMAT, datefmt=LogConfig.DATE_FORMAT
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.propagate = False
            _logger_instance = logger
            logger.info("GBIF Agent logging system initialized (PID: %d)", os.getpid())
            return logger

        except Exception as e:
            # Fallback to console logging
            fallback_logger = logging.getLogger("gbif.agent.fallback")
            fallback_logger.setLevel(logging.WARNING)

            if not fallback_logger.handlers:
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(
                    logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
                )
                fallback_logger.addHandler(console_handler)

            fallback_logger.error(f"Failed to setup file logging: {e}")
            _logger_instance = fallback_logger
            return fallback_logger


def cleanup_old_logs() -> None:
    """Clean up old log files with error handling"""
    try:
        if not os.path.exists(LogConfig.LOG_DIR):
            return

        now = datetime.now(timezone.utc)
        cutoff_time = now.timestamp() - (LogConfig.LOG_TTL_DAYS * 24 * 3600)

        for fname in os.listdir(LogConfig.LOG_DIR):
            fpath = os.path.join(LogConfig.LOG_DIR, fname)

            if not os.path.isfile(fpath):
                continue

            # Only clean up log files
            if not (fname.startswith("gbif_agent") and fname.endswith(".log")):
                continue

            try:
                if os.path.getmtime(fpath) < cutoff_time:
                    os.remove(fpath)
                    logger.debug(f"Cleaned up old log file: {fname}")
            except OSError as e:
                logger.warning(f"Failed to remove old log file {fname}: {e}")

    except Exception as e:
        logger.warning(f"Log cleanup failed: {e}")


# Initialize
logger = setup_logger()
cleanup_old_logs()


# --- Logging Utilities ---
async def log_process_event(event: str, **kwargs) -> None:
    """
    Log a process event with all data

    Args:
        event: The event type/name
        **kwargs: Event data
    """
    try:
        if kwargs:
            details = " | ".join(f"{k}={v}" for k, v in kwargs.items())
            msg = f"{event} | {details}"
        else:
            msg = event

        logger.info(msg)

    except Exception as e:
        logger.error(f"Failed to log event '{event}': {e}")


def log_exception(error: Exception, context: str = "") -> None:
    """
    Log exception with structured information

    Args:
        error: The exception to log
        context: Additional context about where the error occurred
    """
    try:
        # Import here to avoid circular imports
        from src.exceptions import GBIFAgentError

        if isinstance(error, GBIFAgentError):
            error_data = error.to_dict()
            error_msg = f"GBIF_ERROR | {context} | " + " | ".join(
                f"{k}={v}" for k, v in error_data.items() if v is not None
            )
            logger.error(error_msg)
        else:
            logger.error(
                f"EXCEPTION | {context} | Type={type(error).__name__} | Message={str(error)}"
            )

    except Exception as log_error:
        logger.error(
            f"Failed to log exception: {log_error} | Original error: {str(error)}"
        )


@asynccontextmanager
async def wrap_process(process: IChatBioAgentProcess):
    """
    Wrap process methods to add logging with error handling

    Args:
        process: The IChatBioAgentProcess to wrap
    """
    original_log = process.log
    original_create_artifact = process.create_artifact

    async def safe_log_wrapper(msg: str, data: dict | None = None):
        """Safely wrap process.log with error handling"""
        try:
            await log_process_event("process.log", message=msg, data=data)
        except Exception as e:
            logger.error(f"Failed to log process event: {e}")

        try:
            return await original_log(msg, data)
        except Exception as e:
            logger.error(f"Original process.log failed: {e}")
            raise

    async def safe_create_artifact_wrapper(*args, **kwargs):
        """Safely wrap process.create_artifact with error handling"""
        try:
            log_kwargs = {k: v for k, v in kwargs.items() if k != "api_response"}
            await log_process_event(
                "process.create_artifact", args=args, kwargs=log_kwargs
            )
        except Exception as e:
            logger.error(f"Failed to log artifact creation: {e}")

        try:
            return await original_create_artifact(*args, **kwargs)
        except Exception as e:
            logger.error(f"Original create_artifact failed: {e}")
            raise

    # Apply wrappers
    process.log = safe_log_wrapper
    process.create_artifact = safe_create_artifact_wrapper

    try:
        yield process
    finally:
        # Always restore original methods
        try:
            process.log = original_log
            process.create_artifact = original_create_artifact
        except Exception as e:
            logger.error(f"Failed to restore process methods: {e}")


@asynccontextmanager
async def wrap_context(context: ResponseContext):
    """
    Wrap context methods to add logging with error handling

    Args:
        context: The ResponseContext to wrap
    """
    original_reply = context.reply
    original_begin_process = context.begin_process

    async def safe_reply_wrapper(msg: str):
        """Safely wrap context.reply with error handling"""
        try:
            await log_process_event("context.reply", message=msg)
        except Exception as e:
            logger.error(f"Failed to log reply: {e}")

        try:
            return await original_reply(msg)
        except Exception as e:
            logger.error(f"Original context.reply failed: {e}")
            raise

    @asynccontextmanager
    async def safe_begin_process_wrapper(*args, **kwargs):
        """Safely wrap context.begin_process with error handling"""
        try:
            async with original_begin_process(*args, **kwargs) as process:
                async with wrap_process(process) as wrapped_process:
                    yield wrapped_process
        except Exception as e:
            logger.error(f"Process wrapper failed: {e}")
            # Re-raise to maintain original behavior
            raise

    # Apply wrappers
    context.reply = safe_reply_wrapper
    context.begin_process = safe_begin_process_wrapper

    try:
        yield context
    finally:
        # Always restore original methods
        try:
            context.reply = original_reply
            context.begin_process = original_begin_process
        except Exception as e:
            logger.error(f"Failed to restore context methods: {e}")


# Type variable for function parameters
P = TypeVar("P")


def with_logging(entrypoint_id: str):
    """
    Decorator to add comprehensive logging to entrypoint functions
    Args:
        entrypoint_id: Unique identifier for the entrypoint
    Usage:
        @with_logging("find_occurrence_records")
        async def run(context: ResponseContext, request: str, params: ModelParams):
            ...
    """

    def decorator(func: Callable[[ResponseContext, str, P], Any]):
        @wraps(func)
        async def wrapper(context: ResponseContext, request: str):
            start_time = datetime.now(timezone.utc)

            try:
                logger.info(f"ENTRY | Entrypoint={entrypoint_id} | Request={request}")

                # Execute with logging context
                async with wrap_context(context):
                    result = await func(context, request)

                # Log successful completion
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                logger.info(
                    f"SUCCESS | Entrypoint={entrypoint_id} | Duration={duration:.3f}s"
                )

                return result

            except Exception as e:
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                log_exception(
                    e, f"Entrypoint={entrypoint_id} | Duration={duration:.3f}s"
                )
                logger.error(
                    f"ERROR | Entrypoint={entrypoint_id} | Duration={duration:.3f}s | Error={type(e).__name__}: {str(e)}"
                )

                # Re-raise to maintain original behavior
                raise

        return wrapper

    return decorator


# Health check function
def get_logging_health() -> dict[str, Any]:
    """Get logging system health information"""
    try:
        return {
            "status": "healthy",
            "log_file": LogConfig.LOG_FILE,
            "log_level": LogConfig.LOG_LEVEL,
            "log_dir_exists": os.path.exists(LogConfig.LOG_DIR),
            "log_file_exists": os.path.exists(LogConfig.LOG_FILE),
            "handlers_count": len(logger.handlers) if logger else 0,
            "config": {
                "ttl_days": LogConfig.LOG_TTL_DAYS,
                "backup_count": LogConfig.BACKUP_COUNT,
                "max_log_size": LogConfig.MAX_LOG_SIZE,
            },
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
