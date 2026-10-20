"""画面で利用する認証ポリシーを取得する。"""

from modules.accounts.application.dto.auth import AuthPolicy


class GetAuthPolicyUseCase:
    def __init__(self, policy: AuthPolicy) -> None:
        self.policy = policy

    def execute(self) -> AuthPolicy:
        return self.policy
