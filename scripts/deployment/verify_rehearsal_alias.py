"""本番aliasを固定project/deploymentと照合。トークン・API応答は出さない。"""

import json
import os
import re
import urllib.parse
import urllib.request


def verify():
    expected = os.environ["EXPECTED_DEPLOYMENT"]
    token = os.environ["VERCEL_TOKEN"]
    if expected.startswith("https://"):
        url = urllib.parse.urlsplit(expected)
        if (
            url.scheme != "https"
            or url.path not in ("", "/")
            or url.query
            or url.fragment
            or not re.fullmatch(r"grad-checker-[a-z0-9-]+\.vercel\.app", url.netloc)
        ):
            raise ValueError("Invalid stage URL")
        deployment_request = urllib.request.Request(
            "https://api.vercel.com/v13/deployments/"
            + url.netloc
            + "?teamId=team_tZDGBnNdyZxvlZvkV86h6SGv",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(deployment_request, timeout=45) as response:
            deployment = json.load(response)
        if (
            (deployment.get("projectId") or deployment.get("project", {}).get("id"))
            != "prj_QgFMi1xMYgrYLGPI1Yi9h0kdkNzW"
            or deployment.get("target") != "production"
            or deployment.get("readyState") != "READY"
        ):
            raise ValueError(
                "Stage is not a ready production build of the fixed project"
            )
        expected = deployment["id"]
    if not re.fullmatch(r"dpl_[A-Za-z0-9]+", expected):
        raise ValueError("Invalid deployment id")
    request = urllib.request.Request(
        "https://api.vercel.com/v4/aliases/grad-checker-chi.vercel.app"
        "?teamId=team_tZDGBnNdyZxvlZvkV86h6SGv&projectId=prj_QgFMi1xMYgrYLGPI1Yi9h0kdkNzW",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        alias = json.load(response)
    allowed = {expected}
    if os.environ.get("ALLOW_BASELINE") == "1":
        allowed.add("dpl_GEXV2AgfCoGPq8CZsSMfb1nQJZ6C")
    if (
        alias.get("projectId") != "prj_QgFMi1xMYgrYLGPI1Yi9h0kdkNzW"
        or alias.get("deploymentId") not in allowed
    ):
        raise ValueError("Production alias differs from reviewed target")
    print(json.dumps({"alias_verified": True, "deployment": alias["deploymentId"]}))


if __name__ == "__main__":
    try:
        verify()
    except Exception as error:  # noqa: BLE001 -- Secret・API応答を出さない
        print(json.dumps({"alias_verified": False, "error_type": type(error).__name__}))
        raise SystemExit(1) from None
