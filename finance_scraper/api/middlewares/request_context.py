
import time
from uuid import uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RequestContextMiddleware:
    """Add a correlation ID and response timing to every HTTP request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        request_id: str = next(
            (
                value.decode('latin-1')
                for key, value in scope.get('headers', [])
                if key.lower() == b'x-request-id' and value
            ),
            str(uuid4()),
        )
        started_at: float = time.perf_counter()

        async def send_with_context(message: Message) -> None:
            if message['type'] == 'http.response.start':
                headers: list[tuple[bytes, bytes]] = list(
                    message.get('headers', [])
                )
                headers.extend(
                    [
                        (b'x-request-id', request_id.encode('latin-1')),
                        (
                            b'x-response-time-ms',
                            f'{(time.perf_counter() - started_at) * 1000:.2f}'.encode(
                                'ascii'
                            ),
                        ),
                    ]
                )
                message = {**message, 'headers': headers}
            await send(message)

        await self.app(scope, receive, send_with_context)
