"""SMTPメール配送。原トークンをログやAPI応答へ出さない。"""

import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import urlencode

from modules.accounts.grad_checker_accounts.application.auth import AuthError


class SmtpVerificationMailer:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        sender: str,
        origin: str,
        starttls: bool,
        minutes: int,
    ) -> None:
        self.host, self.port = host, port
        self.username, self.password = username, password
        self.sender, self.origin = sender, origin
        self.starttls, self.minutes = starttls, minutes

    def send(self, email: str, token: str) -> None:
        if not self.host or not self.sender:
            raise AuthError("mail_unavailable")
        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = email
        message["Subject"] = "卒業要件チェッカー：メールアドレスの確認"
        link = self.origin + "/#" + urlencode({"verification_token": token})
        message.set_content(
            f"以下のリンクを開き、パスワードを設定すると登録が完了します。\n\n{link}\n\n"
            f"リンクの有効期限は{self.minutes}分です。心当たりがない場合は無視してください。\n"
            "大学の公式システムではありません。大学アカウントのパスワードは入力しないでください。"
        )
        try:
            with smtplib.SMTP(self.host, self.port, timeout=5) as smtp:
                if self.starttls:
                    smtp.starttls(context=ssl.create_default_context())
                if self.username:
                    smtp.login(self.username, self.password)
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException) as error:
            raise AuthError("mail_unavailable") from error
