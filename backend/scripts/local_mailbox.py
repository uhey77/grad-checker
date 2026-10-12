"""ローカル検証専用のSMTP受信箱。メールを外部へ配送しない。"""

import argparse
import html
import json
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from urllib.parse import urlsplit

from aiosmtpd.controller import Controller


class Mailbox:
    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []
        self.lock = Lock()

    async def handle_DATA(self, _server, _session, envelope) -> str:  # noqa: N802
        message = BytesParser(policy=policy.default).parsebytes(
            envelope.original_content
        )
        body = message.get_body(preferencelist=("plain",))
        with self.lock:
            self.messages.append(
                {
                    "to": str(message.get("To", "")),
                    "subject": str(message.get("Subject", "")),
                    "body": body.get_content() if body else "",
                }
            )
        return "250 OK"


def create_handler(mailbox: Mailbox):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            with mailbox.lock:
                messages = list(mailbox.messages)
            if self.path == "/messages":
                data = json.dumps(messages, ensure_ascii=False).encode()
                media = "application/json"
            elif self.path == "/":
                content = (
                    "<h1>開発用メール受信箱</h1><p>外部へメールは送信しません。"
                    "再読み込みすると新着を表示します。</p>"
                )
                for message in reversed(messages):
                    content += (
                        f"<article><h2>{html.escape(message['subject'])}</h2>"
                        f"<p>{html.escape(message['to'])}</p>"
                        f"<pre>{html.escape(message['body'])}</pre>"
                    )
                    for line in message["body"].splitlines():
                        parsed = urlsplit(line)
                        if parsed.scheme in {"http", "https"} and parsed.hostname:
                            content += (
                                f'<p><a href="{html.escape(line, quote=True)}" '
                                'rel="noreferrer">確認リンクを開く</a></p>'
                            )
                    content += "</article>"
                data = (
                    "<!doctype html><html lang='ja'><meta charset='utf-8'>"
                    "<title>開発用メール受信箱</title><style>"
                    "body{font-family:system-ui;max-width:900px;"
                    "margin:32px auto;padding:16px}"
                    "pre{white-space:pre-wrap;overflow-wrap:anywhere}"
                    "article{border-top:1px solid #ccc;padding:20px 0}</style>"
                    + content
                    + "</html>"
                ).encode()
                media = "text/html; charset=utf-8"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", media)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, format: str, *args) -> None:  # noqa: A002
            pass

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smtp-port", type=int, default=1025)
    parser.add_argument("--http-port", type=int, default=8025)
    args = parser.parse_args()
    mailbox = Mailbox()
    controller = Controller(mailbox, hostname="127.0.0.1", port=args.smtp_port)
    controller.start()
    server = ThreadingHTTPServer(("127.0.0.1", args.http_port), create_handler(mailbox))
    print(
        f"開発用受信箱: http://127.0.0.1:{args.http_port} "
        f"/ SMTP: 127.0.0.1:{args.smtp_port}",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        controller.stop()


if __name__ == "__main__":
    main()
