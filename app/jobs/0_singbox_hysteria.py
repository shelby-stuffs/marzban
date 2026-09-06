from app import app, logger, scheduler
from config import SINGBOX_HEALTH_CHECK_INTERVAL, SINGBOX_HYSTERIA_ENABLED

if SINGBOX_HYSTERIA_ENABLED:
    from app.singbox.runtime import runtime

    @app.on_event("startup")
    def start_singbox_hysteria():
        logger.info("Starting standalone sing-box Hysteria2 core")
        runtime._apply_safely()
        scheduler.add_job(
            runtime._apply_safely,
            "interval",
            seconds=SINGBOX_HEALTH_CHECK_INTERVAL,
            coalesce=True,
            max_instances=1,
        )

    @app.on_event("shutdown")
    def stop_singbox_hysteria():
        runtime.core.stop()
