"""Go公開APIの仕様を生成する。ブリッジ用FastAPIの仕様は使用しない。"""

import argparse
import copy
import json
from pathlib import Path

from pydantic import BaseModel, TypeAdapter

from modules.accounts.grad_checker_accounts.application.profile import (
    Profile,
    ProgramOption,
)
from modules.grades.grad_checker_grades.application.grades import StudentGrades
from modules.requirements.grad_checker_requirements.application.check_results import (
    CheckList,
    SavedCheck,
)
from modules.requirements.grad_checker_requirements.application.student_evaluation import (  # noqa: E501
    StudentDashboard,
    StudentEvaluation,
)
from modules.subjects.grad_checker_subjects.application.course_catalog import (
    CategoryList,
    CourseList,
)
from modules.subjects.grad_checker_subjects.application.subject_list import (
    SubjectList,
    SubjectListProgram,
)

OUTPUT = Path(__file__).resolve().parents[1] / "api/presentation/apidocs/openapi.json"
MAX_REVISION = 9007199254740990


def ref(name: str) -> dict:
    return {"$ref": f"#/components/schemas/{name}"}


def obj(**properties: dict) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def text_schema(**keywords: object) -> dict:
    return {"type": "string", **keywords}


def build_document() -> dict:  # noqa: PLR0915
    schemas: dict = {}

    def response_schema(model: type[BaseModel]) -> dict:
        schema = model.model_json_schema(
            mode="serialization", ref_template="#/components/schemas/{model}"
        )
        definitions = schema.pop("$defs", {})
        for name, definition in {**definitions, model.__name__: schema}.items():
            definition.pop("title", None)
            # model_dumpの出力はnullを含め全フィールドを返す。
            if "properties" in definition:
                definition["required"] = list(definition["properties"])
                definition["additionalProperties"] = False
            if name in schemas and schemas[name] != definition:
                raise ValueError(f"schema name collision: {name}")
            schemas[name] = definition
        return ref(model.__name__)

    for model in (
        Profile,
        ProgramOption,
        StudentGrades,
        StudentEvaluation,
        StudentDashboard,
        SavedCheck,
        CheckList,
        CourseList,
        CategoryList,
        SubjectList,
        SubjectListProgram,
    ):
        response_schema(model)

    schemas["LiveEvaluation"] = copy.deepcopy(schemas["StudentEvaluation"])
    schemas["LiveEvaluation"]["properties"]["recommendations"] = {
        "type": "array",
        "items": ref("CourseRecommendation"),
    }
    schemas["CreatedCheck"] = copy.deepcopy(schemas["SavedCheck"])
    schemas["CreatedCheck"]["properties"]["result"] = ref("LiveEvaluation")
    schemas["Programs"] = obj(programs={"type": "array", "items": ref("ProgramOption")})
    schemas["PreviewPrograms"] = TypeAdapter(list[SubjectListProgram]).json_schema(
        ref_template="#/components/schemas/{model}"
    )
    schemas["PreviewPrograms"].pop("$defs", None)
    schemas["Health"] = obj(status={"const": "ok", "type": "string"})
    schemas["Error"] = obj(detail=text_schema())
    schemas["AuthConfig"] = obj(
        authenticated={"type": "boolean", "const": False},
        policy=obj(
            password_min_length={"type": "integer"},
            password_max_length={"type": "integer"},
        ),
    )
    schemas["AuthSession"] = obj(
        authenticated={"type": "boolean", "const": True},
        student=obj(id=text_schema(format="uuid"), login_name=text_schema()),
        csrf_token=text_schema(minLength=64, maxLength=64),
        expires_at=text_schema(format="date-time"),
    )
    for name, flag in (("Registered", "registered"), ("Recovered", "recovered")):
        schemas[name] = obj(
            **{flag: {"type": "boolean", "const": True}},
            authenticated={"type": "boolean", "const": False},
            recovery_code=text_schema(),
        )
    schemas["LoggedOut"] = obj(authenticated={"type": "boolean", "const": False})
    credentials = {
        "login_name": text_schema(
            minLength=1,
            maxLength=32,
            description="登録時は半角英数字・_の3〜32文字。小文字へ正規化。ログイン・復旧も大文字小文字を区別しない。",
        ),
        "password": text_schema(
            minLength=1,
            maxLength=1024,
            format="password",
            description=(
                "実際の許容文字数はGET /api/auth/configのpolicyを参照。"
                "既定12〜128文字。"
            ),
        ),
    }
    schemas["Credentials"] = obj(**credentials)
    schemas["Recovery"] = obj(
        **credentials, recovery_code=text_schema(minLength=1, maxLength=128)
    )
    revision = {"type": "integer", "minimum": 0, "maximum": MAX_REVISION}
    uuid_input = text_schema(
        description="UUID。標準ハイフン表記を推奨。Goは32桁・波括弧・urn:uuid:形式も正規化して受け付ける。"
    )
    schemas["ProgramSelectionInput"] = obj(
        program_id=uuid_input, curriculum_id=uuid_input, expected_revision=revision
    )
    schemas["CheckRequestInput"] = obj(
        expected_revision=revision,
        completion_answers={
            "type": "array",
            "maxItems": 50,
            "items": ref("CompletionAnswer"),
        },
    )
    schemas["CheckRequestInput"]["required"] = ["expected_revision"]
    grade = copy.deepcopy(schemas["GradeAttempt"])
    grade["properties"]["course_id"] = uuid_input
    grade["allOf"] = [
        {
            "oneOf": [
                {
                    "properties": {
                        "result_status": {"const": "pending"},
                        "grade_code": {"type": "null"},
                    }
                },
                {
                    "properties": {
                        "result_status": {"const": "finalized"},
                        "grade_code": {
                            "type": "string",
                            "enum": ["S", "A", "B", "C", "D", "X"],
                        },
                    }
                },
            ]
        }
    ]
    schemas["GradeAttemptInput"] = grade
    schemas["GradeSetInput"] = obj(
        expected_revision=revision,
        grades={"type": "array", "maxItems": 1000, "items": ref("GradeAttemptInput")},
    )

    headers = {
        "Cache-Control": {
            "description": "保存を禁止する。",
            "schema": {"type": "string", "const": "no-store"},
        }
    }

    def response(schema: str, description: str) -> dict:
        return {
            "description": description,
            "headers": copy.deepcopy(headers),
            "content": {"application/json": {"schema": ref(schema)}},
        }

    paths: dict = {}
    shared_responses: dict = {}

    def operation(
        path: str,
        method: str,
        name: str,
        summary: str,
        output: str,
        *,
        public: bool = False,
        body: str | None = None,
        errors: dict[int, list[str]] | None = None,
        description: str = "",
        csrf: bool = False,
        origin: bool = False,
        status: int = 200,
        parameters: list | None = None,
    ) -> None:
        responses = {
            str(status): response(
                output,
                "成功。未達成の判定もHTTP成功。"
                if output in {"LiveEvaluation", "CreatedCheck", "StudentDashboard"}
                else "成功。",
            )
        }
        failures = {405: ["HTTPメソッドが不正です。"]}
        if not public:
            failures[401] = [
                "ログインしてください。",
                "ユーザー名またはパスワードを確認してください。",
            ]
        if (
            path != "/api/health"
            and not path.startswith("/api/dev/")
            and not any(p.get("in") == "query" for p in parameters or [])
        ):
            failures[422] = ["クエリパラメーターは指定できません。"]
        if csrf or origin:
            failures[403] = ["操作を確認できません。画面を再読み込みしてください。"]
            if origin:
                failures[403].append(
                    "アクセス元を確認できません。画面を再読み込みしてください。"
                )
        for code, details in (errors or {}).items():
            failures.setdefault(code, []).extend(details)
        for code, details in failures.items():
            result = response("Error", " / ".join(dict.fromkeys(details)))
            result["content"]["application/json"]["examples"] = {
                f"case_{i + 1}": {"value": {"detail": detail}}
                for i, detail in enumerate(dict.fromkeys(details))
            }
            if code == 405:
                result["headers"]["Allow"] = {
                    "schema": {"type": "string"},
                    "description": "そのパスで許可するメソッド。",
                }
            shared_name = next(
                (key for key, value in shared_responses.items() if value == result),
                f"{name}Error{code}",
            )
            shared_responses[shared_name] = result
            responses[str(code)] = {"$ref": f"#/components/responses/{shared_name}"}
        params = list(parameters or [])
        if origin or csrf:
            params.append({"$ref": "#/components/parameters/Origin"})
        item = {
            "operationId": name,
            "summary": summary,
            "description": description
            + "\n\n"
            + (
                "未知・重複・空のクエリは拒否する。"
                if parameters and method == "get"
                else "クエリは使用しない（指定すると422）。"
                if path != "/api/health" and not path.startswith("/api/dev/")
                else "クエリは使用しない（実装は無視する）。"
            ),
            "tags": [
                "開発用"
                if path.startswith("/api/dev/")
                else "認証"
                if path.startswith("/api/auth/")
                else "学生API"
            ],
            "security": (
                [{"sessionCookie": [], "csrfToken": []}]
                if csrf
                else [{"sessionCookie": []}]
                if not public
                else []
            ),
            "responses": responses,
        }
        if params:
            item["parameters"] = params
        if body:
            item["requestBody"] = {
                "required": True,
                "description": "application/json。全項目必須。未知・重複キーを拒否。",
                "content": {"application/json": {"schema": ref(body)}},
            }
        paths.setdefault(path, {})[method] = item

    auth_errors = {
        422: [
            "入力形式が不正です。",
            "JSON形式で入力してください。",
            "入力項目が重複しています。",
            "入力項目は文字列で指定してください。",
            "必要な入力項目を指定してください。",
            "入力項目が不正です。",
            "入力が長すぎます。",
            "ユーザー名は半角英数字・アンダースコアの3〜32文字で入力してください。",
            "パスワードの文字数が設定された範囲外です。",
        ],
        400: ["接続元を確認できません。"],
        429: ["試行回数の上限に達しました。時間をおいて再試行してください。"],
        502: ["認証サービスに接続できません。時間をおいて再試行してください。"],
        503: ["認証処理を利用できません。時間をおいて再試行してください。"],
    }
    operation(
        "/api/health",
        "get",
        "health",
        "Goの稼働確認",
        "Health",
        public=True,
        description="Python・DBの稼働を保証しない。",
    )
    operation(
        "/api/auth/config",
        "get",
        "authConfig",
        "パスワード方針",
        "AuthConfig",
        public=True,
        errors={502: auth_errors[502], 503: auth_errors[503]},
    )
    for action, output in (
        ("register", "Registered"),
        ("recover", "Recovered"),
        ("login", "AuthSession"),
    ):
        errors = copy.deepcopy(auth_errors)
        if action == "register":
            errors[409] = [
                "このユーザー名は使用されています。別のユーザー名を指定してください。"
            ]
        elif action == "recover":
            errors[400].append("ユーザー名または復旧コードを確認してください。")
        else:
            errors[401] = ["ユーザー名またはパスワードを確認してください。"]
        operation(
            f"/api/auth/{action}",
            "post",
            f"auth{action.title()}",
            {
                "register": "新規登録",
                "recover": "復旧コードでパスワード再設定",
                "login": "ログイン",
            }[action],
            output,
            public=True,
            body="Recovery" if action == "recover" else "Credentials",
            origin=True,
            status=201 if action == "register" else 200,
            errors=errors,
            description=(
                "本文上限8192 bytes。上限超過も422。復旧コードは登録・復旧時だけ"
                "返す。ログインのみCookieを設定。復旧は全セッションを失効させる。"
            ),
        )
    for action, output in (("session", "AuthSession"), ("logout", "LoggedOut")):
        operation(
            f"/api/auth/{action}",
            "get" if action == "session" else "post",
            f"auth{action.title()}",
            "セッション取得" if action == "session" else "ログアウト",
            output,
            csrf=action == "logout",
            origin=action == "logout",
            errors={502: auth_errors[502], 503: auth_errors[503]},
            description="セッション未認証時はCookieを削除。ログアウト成功時も削除。本文は使用しない。",
        )

    def service_errors(subject: str, service: str) -> dict:
        return {
            502: [
                f"{service}サービスに接続できません。時間をおいて再試行してください。",
                f"{service}サービスの応答を読み込めません。",
            ],
            503: [f"{subject}を処理できません。時間をおいて再試行してください。"],
        }

    conflict = "別の画面でデータが更新されました。再取得してから保存してください。"
    selection_detail = "所属・カリキュラム・更新版を正しい形式で指定してください。"
    for path, method, name, output in (
        ("/api/programs", "get", "listPrograms", "Programs"),
        ("/api/me", "get", "getProfile", "Profile"),
        ("/api/me/program", "put", "saveProgram", "Profile"),
    ):
        errors = service_errors("所属情報", "所属")
        if method == "put":
            errors.update(
                {
                    409: [conflict],
                    413: [selection_detail],
                    415: ["JSON形式で送信してください。"],
                    422: [
                        selection_detail,
                        "所属とカリキュラムの組合せが不正です。選択肢を再取得してください。",
                    ],
                }
            )
        operation(
            path,
            method,
            name,
            {
                "listPrograms": "所属の選択肢",
                "getProfile": "本人プロフィール",
                "saveProgram": "本人の所属を保存",
            }[name],
            output,
            errors=errors,
            csrf=method == "put",
            body="ProgramSelectionInput" if method == "put" else None,
            description=(
                "所属と成績は同じdata_revisionを共有する。"
                "所属保存の本文上限4096 bytes。"
            ),
        )
    for method in ("get", "put"):
        errors = service_errors("成績", "成績")
        if method == "put":
            errors.update(
                {
                    400: [
                        "選択した科目が見つかりません。科目一覧を再読み込みしてください。"
                    ],
                    409: [conflict],
                    413: ["送信する成績の量が上限を超えています。"],
                    415: ["JSON形式で送信してください。"],
                    422: [
                        "成績の送信形式が不正です。expected_revisionとgradesだけを指定してください。",
                        "一度に保存できる成績の件数を超えています。",
                        "成績の形式が不正です。科目・履修回次・成績・年度・学期を確認してください。",
                        "同じ科目の履修回次が重複しています。",
                        "履修回次は1から順に入力してください。再履修は不合格（D・X）の後だけ追加できます。",
                    ],
                }
            )
        operation(
            "/api/me/grades",
            method,
            "getGrades" if method == "get" else "saveGrades",
            "本人成績の取得" if method == "get" else "本人成績の全集合置換",
            "StudentGrades",
            body="GradeSetInput" if method == "put" else None,
            csrf=method == "put",
            errors=errors,
            description=(
                "保存は全集合置換。空配列は全取消。回次は1から連番で直前が確定不合格(D/X"
                ")の場合だけ再履修できる。所属保存と版を共有。本文上限256 KiB。"
            ),
        )

    course_errors = {
        409: [
            "所属課程を設定してから科目を表示してください。",
            "所属課程のデータが見つかりません。所属を設定し直してください。",
            "科目分類のデータが不整合です。課程・科目データを確認してください。",
        ],
        503: ["科目データを読み込めません。時間をおいて再試行してください。"],
        502: [
            "科目サービスに接続できません。時間をおいて再試行してください。",
            "科目サービスの応答を読み込めません。",
        ],
        504: ["Pythonサービスの応答がタイムアウトしました。"],
    }
    filters = []
    for key in ("category_id", "faculty", "department", "semester", "q"):
        schema = {"type": "string", "minLength": 1, "maxLength": 100}
        if key == "semester":
            schema["enum"] = ["first", "second"]
        filters.append(
            {
                "name": key,
                "in": "query",
                "schema": schema,
                "description": "各1回。複数条件はAND。",
            }
        )
    course_errors[422] = [
        "絞り込み条件の形式が不正です。",
        "未対応の絞り込み条件が指定されています。",
        "絞り込み条件は各1回、1〜100文字で指定してください。",
        "科目区分IDの形式が不正です。",
        "開講学期はfirst（前期）またはsecond（後期）で指定してください。",
        "指定した科目区分は本人の課程にありません。科目区分を選び直してください。",
    ]
    operation(
        "/api/courses",
        "get",
        "listCourses",
        "本人課程から見た科目一覧",
        "CourseList",
        errors=course_errors,
        parameters=filters,
        description=(
            "category_idは子孫分類も一致。faculty/department"
            "は開講元名の完全一致。qは科目名・コードの大小文字を区別しない部分一致。se"
            "mesterは開講学期。placement:nullは本人課程での算入先未確"
            "定。"
        ),
    )
    operation(
        "/api/categories",
        "get",
        "listCategories",
        "本人課程の分類階層",
        "CategoryList",
        errors={k: v for k, v in course_errors.items() if k != 422},
    )

    evaluation_errors = {
        400: ["保存済みの成績に未知の科目が含まれています。"],
        409: [
            "所属が未設定です。所属設定を保存してから判定してください。",
            "必要な単位換算・他学部算入の規則が未確認のため、卒業要件を判定できません。",
            "他学部科目の算入先を決めるため、履修年度・学期が必要です。他学部科目の未入力の年度・学期を入力して保存し、再度判定してください。",
            "所属課程外の修得科目に、算入先が未登録の科目があります。対象科目と算入先のマスタ整備が必要です。",
            "卒業要件の科目・条件・算入規則の設定が不足しているか、不整合があります。",
            "保存済みの成績または判定マスタが不正なため、判定できません。",
            "保存済みの成績データが不正なため、判定できません。",
            "保存済みの履修回次が不正なため、判定できません。",
            "保存済みの履修回次が重複しているため、判定できません。",
        ],
        502: [
            "卒業要件の判定サービスに接続できません。時間をおいて再試行してください。",
            "卒業要件の判定サービスの応答を読み込めません。",
        ],
        503: ["卒業要件の判定を処理できません。時間をおいて再試行してください。"],
    }
    for path, name, output in (
        ("/api/me/dashboard", "dashboard", "StudentDashboard"),
        ("/api/me/graduation-requirements", "evaluate", "LiveEvaluation"),
    ):
        operation(
            path,
            "get",
            name,
            "最新判定の概要" if name == "dashboard" else "最新の卒業要件判定",
            output,
            errors=evaluation_errors,
            description=(
                "読取り専用。履歴・data_revisionを更新しない。修得と算入を区別。"
                "適用年度のunverifiedだけでは停止しない。"
            ),
        )
    check_errors = copy.deepcopy(evaluation_errors)
    check_errors[503].append(
        "判定履歴を処理できません。時間をおいて再試行してください。"
    )
    for method, output in (("get", "CheckList"), ("post", "CreatedCheck")):
        errors = copy.deepcopy(check_errors)
        params = None
        if method == "post":
            errors[409].append(conflict)
            errors.update(
                {
                    413: ["送信内容が上限を超えています。"],
                    415: ["JSON形式で送信してください。"],
                    422: [
                        "判定の送信形式が不正です。expected_revisionと修了条件の回答を確認してください。"
                    ],
                }
            )
        else:
            errors[422] = [
                "履歴の表示範囲が不正です。limitは1〜100、offsetは0以上の整数で各1回まで指定してください。"
            ]
            params = [
                {
                    "name": key,
                    "in": "query",
                    "schema": {
                        "type": "integer",
                        "minimum": minimum,
                        "maximum": maximum,
                        "default": default,
                    },
                    "description": "符号・小数なしの10進整数。各1回。",
                }
                for key, minimum, maximum, default in (
                    ("limit", 1, 100, 20),
                    ("offset", 0, MAX_REVISION, 0),
                )
            ]
        operation(
            "/api/checks",
            method,
            "listChecks" if method == "get" else "createCheck",
            "本人の判定履歴一覧" if method == "get" else "判定して履歴へ保存",
            output,
            errors=errors,
            parameters=params,
            csrf=method == "post",
            body="CheckRequestInput" if method == "post" else None,
            status=201 if method == "post" else 200,
            description=(
                "一覧はcreated_at降順・同時刻id昇順。POSTは本人版を照合し保存"
                "commit後に201。失敗時は履歴を残さない。本文上限1 KiB。"
            ),
        )
    check_errors[404] = ["判定履歴が見つかりません。"]
    operation(
        "/api/checks/{id}",
        "get",
        "getCheck",
        "本人の過去の判定",
        "SavedCheck",
        errors=check_errors,
        parameters=[
            {"name": "id", "in": "path", "required": True, "schema": uuid_input}
        ],
        description=(
            "形式不正・他人・存在しないIDは同じ404。現在のマスタで再計算しない。推薦"
            "導入前の保存結果だけrecommendations:null。"
        ),
    )

    preview_errors = {
        404: [
            "科目一覧の開発用表示は無効です。",
            "選択したカリキュラムが見つかりません。",
        ],
        409: ["科目分類のデータが不整合です。課程・科目データを確認してください。"],
        500: ["科目データの取得中に予期しないエラーが発生しました。"],
        503: ["科目データを読み込めません。時間をおいて再試行してください。"],
        504: ["Pythonサービスの応答がタイムアウトしました。"],
        502: [
            "Pythonサービスに接続できません。起動状態を確認してください。",
            "Pythonサービスの応答を読み込めません。",
        ],
    }
    operation(
        "/api/dev/subject-list/programs",
        "get",
        "previewPrograms",
        "開発用課程一覧",
        "PreviewPrograms",
        public=True,
        errors=preview_errors,
        description="-subject-list-preview指定時だけ有効。通常・本番は404。学生データを返さない。",
    )
    preview_errors[422] = ["カリキュラムIDの形式が不正です。"]
    operation(
        "/api/dev/subject-list/{curriculum_id}",
        "get",
        "previewSubjects",
        "開発用科目一覧",
        "SubjectList",
        public=True,
        errors=preview_errors,
        parameters=[
            {
                "name": "curriculum_id",
                "in": "path",
                "required": True,
                "schema": uuid_input,
            }
        ],
        description="-subject-list-preview指定時だけ有効。通常・本番は404。学生データを返さない。",
    )

    cookie_header = {
        "schema": {"type": "string"},
        "description": (
            "grad_checker_session。Path=/; HttpOnly;"
            " SameSite=Lax。public-originがHTTPSならSec"
            "ure。セッション原値はJSONに返さない。"
        ),
    }
    for path, code in (
        ("/api/auth/login", "200"),
        ("/api/auth/logout", "200"),
        ("/api/auth/session", "401"),
    ):
        method = "get" if path.endswith("session") else "post"
        target = paths[path][method]["responses"][code]
        if "$ref" in target:
            # Set-Cookieはこのoperationだけの応答ヘッダー。
            target = copy.deepcopy(shared_responses[target["$ref"].split("/")[-1]])
            paths[path][method]["responses"][code] = target
        target["headers"]["Set-Cookie"] = cookie_header
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "grad-checker Go公開API",
            "version": "1.0.0",
            "description": (
                "外部HTTPはGo。Pythonの/bridge/*、/docs、/open"
                "api.jsonは公開契約に含めない。本人IDはCookieセッションから決"
                "定。JSON応答はCache-Control:no-store。認証済みの変"
                "更はOriginとX-CSRF-Tokenを両方確認。"
            ),
        },
        "servers": [
            {
                "url": "/",
                "description": "Swagger UIと同じOrigin。ローカルはViteのプロキシ経由。",
            }
        ],
        "paths": paths,
        "components": {
            "schemas": schemas,
            "responses": shared_responses,
            "securitySchemes": {
                "sessionCookie": {
                    "type": "apiKey",
                    "in": "cookie",
                    "name": "grad_checker_session",
                    "description": (
                        "ログインで設定するHttpOnly Cookie。Swagger UIには手"
                        "入力せず、ブラウザーから同じOriginへ自動送信する。"
                    ),
                },
                "csrfToken": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-CSRF-Token",
                    "description": (
                        "ログインまたはセッション応答のcsrf_token（64文字）。Author"
                        "izeへ入力。ブラウザーストレージへ保存しない。"
                    ),
                },
            },
            "parameters": {
                "Origin": {
                    "name": "Origin",
                    "in": "header",
                    "required": True,
                    "schema": text_schema(default="http://127.0.0.1:5173"),
                    "description": (
                        "ブラウザーが現在のOriginを送信。Go/PythonのPUBLIC_OR"
                        "IGINと一致させる。既定http://127.0.0.1:5173。"
                    ),
                }
            },
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="生成せずコミット済み仕様との差分を検出"
    )
    args = parser.parse_args()
    rendered = json.dumps(build_document(), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text() != rendered:
            parser.exit(
                1,
                "OpenAPIが古くなっています。make api-docs-build を実行してください。\n",
            )
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(rendered)


if __name__ == "__main__":
    main()
