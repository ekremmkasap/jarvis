"""
Real-time Web Monitoring Dashboard Server
Provides WebSocket and REST API for real-time metrics updates
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

try:
    from aiohttp import web
    from aiohttp.web import WebSocketResponse
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    web = None
    WebSocketResponse = None

from server.monitoring.execution_metrics import ExecutionMetricsCollector
from server.monitoring.health_check import HealthChecker


class DashboardServer:
    """Real-time dashboard web server with WebSocket support"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8888,
        log_dir: Path | str = "server/logs",
        static_dir: Path | str = "apps/monitoring-dashboard"
    ):
        """Initialize dashboard server"""
        if not AIOHTTP_AVAILABLE:
            raise ImportError("aiohttp is required for DashboardServer")

        self.host = host
        self.port = port
        self.log_dir = Path(log_dir)
        self.static_dir = Path(static_dir)
        self.metrics_collector = ExecutionMetricsCollector(log_dir=self.log_dir)
        self.health_checker = HealthChecker(log_dir=self.log_dir)
        self.logger = self._build_logger()
        self.app: Optional[web.Application] = None
        self.websocket_clients: set[WebSocketResponse] = set()

    def _build_logger(self) -> logging.Logger:
        """Build logger for dashboard server"""
        logger = logging.getLogger("jarvis.monitoring.dashboard")
        logger.setLevel(logging.INFO)
        logger.propagate = False

        if not any(
            isinstance(h, logging.FileHandler)
            and Path(h.baseFilename) == self.log_dir / "dashboard.log"
            for h in logger.handlers
        ):
            handler = logging.FileHandler(
                self.log_dir / "dashboard.log",
                encoding="utf-8"
            )
            handler.setFormatter(
                logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
            )
            logger.addHandler(handler)

        return logger

    def _create_app(self) -> web.Application:
        """Create aiohttp application with routes"""
        app = web.Application()

        # Routes
        app.router.add_get("/", self._handle_index)
        app.router.add_get("/api/metrics", self._handle_metrics)
        app.router.add_get("/api/health", self._handle_health)
        app.router.add_get("/api/chart-data", self._handle_chart_data)
        app.router.add_get("/api/ws", self._handle_websocket)
        app.router.add_static("/", path=self.static_dir, name="static")

        return app

    async def _handle_index(self, request: web.Request) -> web.Response:
        """Serve index.html"""
        try:
            index_path = self.static_dir / "index.html"
            if not index_path.exists():
                return web.Response(
                    text="Dashboard frontend not found. Create apps/monitoring-dashboard/index.html",
                    status=404
                )
            return web.FileResponse(index_path, content_type="text/html")
        except Exception as e:
            self.logger.error(f"Error serving index: {e}")
            return web.Response(text=str(e), status=500)

    async def _handle_metrics(self, request: web.Request) -> web.Response:
        """Get current metrics snapshot"""
        try:
            stats = self.metrics_collector.get_stats(time_window_minutes=60)
            health_status = self.health_checker.get_status(metrics_data=stats)

            response = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "stats": stats,
                "health": {
                    "status": health_status.status,
                    "components": health_status.components,
                },
            }

            return web.json_response(response)
        except Exception as e:
            self.logger.error(f"Error getting metrics: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_health(self, request: web.Request) -> web.Response:
        """Get health status"""
        try:
            response, status_code = self.health_checker.get_health_endpoint_response()
            return web.json_response(response, status=status_code)
        except Exception as e:
            self.logger.error(f"Error checking health: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_chart_data(self, request: web.Request) -> web.Response:
        """Get historical chart data for trends"""
        try:
            # Get last 100 metrics for trend analysis
            metrics = self.metrics_collector.get_recent_metrics(limit=100)

            if not metrics:
                return web.json_response({
                    "success_rate_trend": [],
                    "latency_trend": [],
                    "throughput_trend": [],
                    "cache_performance": [],
                })

            # Group by 5-minute windows
            windows: dict[str, dict[str, Any]] = {}

            for metric in metrics:
                # Parse timestamp and round to 5-minute window
                ts = datetime.fromisoformat(metric.timestamp)
                window_time = ts.replace(minute=(ts.minute // 5) * 5, second=0, microsecond=0)
                window_key = window_time.isoformat()

                if window_key not in windows:
                    windows[window_key] = {
                        "time": window_key,
                        "total": 0,
                        "success": 0,
                        "durations": [],
                        "cache_hits": 0,
                    }

                windows[window_key]["total"] += 1
                if metric.status == "success":
                    windows[window_key]["success"] += 1
                windows[window_key]["durations"].append(metric.duration_seconds)
                if metric.cache_hit:
                    windows[window_key]["cache_hits"] += 1

            # Calculate trend data
            sorted_windows = sorted(windows.items())

            success_rate_trend = [
                {
                    "time": w["time"],
                    "rate": round((w["success"] / w["total"] * 100) if w["total"] > 0 else 0, 1)
                }
                for _, w in sorted_windows
            ]

            latency_trend = [
                {
                    "time": w["time"],
                    "avg": round(sum(w["durations"]) / len(w["durations"]), 3) if w["durations"] else 0
                }
                for _, w in sorted_windows
            ]

            throughput_trend = [
                {
                    "time": w["time"],
                    "count": w["total"]
                }
                for _, w in sorted_windows
            ]

            cache_performance = [
                {
                    "time": w["time"],
                    "hit_rate": round((w["cache_hits"] / w["total"] * 100) if w["total"] > 0 else 0, 1)
                }
                for _, w in sorted_windows
            ]

            return web.json_response({
                "success_rate_trend": success_rate_trend,
                "latency_trend": latency_trend,
                "throughput_trend": throughput_trend,
                "cache_performance": cache_performance,
            })
        except Exception as e:
            self.logger.error(f"Error getting chart data: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_websocket(self, request: web.Request) -> WebSocketResponse:
        """Handle WebSocket connections for real-time updates"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.websocket_clients.add(ws)
        self.logger.info(f"WebSocket client connected. Total: {len(self.websocket_clients)}")

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    if msg.data == "ping":
                        await ws.send_str("pong")
                elif msg.type == web.WSMsgType.ERROR:
                    self.logger.error(f"WebSocket error: {ws.exception()}")
        except Exception as e:
            self.logger.error(f"WebSocket error: {e}")
        finally:
            self.websocket_clients.discard(ws)
            self.logger.info(f"WebSocket client disconnected. Total: {len(self.websocket_clients)}")

        return ws

    async def _broadcast_metrics(self) -> None:
        """Broadcast metrics to all connected WebSocket clients"""
        while True:
            try:
                if self.websocket_clients:
                    stats = self.metrics_collector.get_stats(time_window_minutes=60)
                    health_status = self.health_checker.get_status(metrics_data=stats)

                    data = {
                        "type": "metrics_update",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "stats": stats,
                        "health": {
                            "status": health_status.status,
                            "components": health_status.components,
                        },
                    }

                    # Send to all connected clients
                    disconnected = set()
                    for ws in self.websocket_clients:
                        try:
                            await ws.send_json(data)
                        except Exception as e:
                            self.logger.debug(f"Error sending to WebSocket client: {e}")
                            disconnected.add(ws)

                    # Clean up disconnected clients
                    self.websocket_clients -= disconnected

                await asyncio.sleep(5)  # Update every 5 seconds
            except Exception as e:
                self.logger.error(f"Error broadcasting metrics: {e}")
                await asyncio.sleep(5)

    async def start(self) -> None:
        """Start the dashboard server"""
        if not AIOHTTP_AVAILABLE:
            raise RuntimeError("aiohttp is required to start DashboardServer")

        self.app = self._create_app()
        self.logger.info(f"Starting dashboard server on {self.host}:{self.port}")

        # Start background task for broadcasting metrics
        asyncio.create_task(self._broadcast_metrics())

        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()

        self.logger.info(f"Dashboard server running on http://{self.host}:{self.port}")
        print(f"Dashboard available at http://{self.host}:{self.port}")

        # Keep server running
        try:
            while True:
                await asyncio.sleep(3600)
        except KeyboardInterrupt:
            self.logger.info("Dashboard server shutting down...")
            await runner.cleanup()


def run_dashboard_server(
    host: str = "localhost",
    port: int = 8888,
    log_dir: Path | str = "server/logs",
    static_dir: Path | str = "apps/monitoring-dashboard"
) -> None:
    """Run the dashboard server in blocking mode"""
    if not AIOHTTP_AVAILABLE:
        raise ImportError("aiohttp is required. Install with: pip install aiohttp")

    server = DashboardServer(
        host=host,
        port=port,
        log_dir=log_dir,
        static_dir=static_dir
    )

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\nDashboard server stopped")


if __name__ == "__main__":
    import sys

    # Parse command line arguments
    host = "localhost"
    port = 8888

    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        port = int(sys.argv[2])

    run_dashboard_server(host=host, port=port)
