"""検証済みSHAタグだけを既定のCloud Runマニフェストへ反映する。"""

import os
import re
from pathlib import Path

image = os.environ["DEPLOY_IMAGE"]
if not re.fullmatch(
    r"asia-northeast1-docker\.pkg\.dev/grad-checker-512505/grad-checker/api:[0-9a-f]{40}",
    image,
):
    raise SystemExit("Unexpected image target or missing commit SHA")
print(Path("infra/cloud-run.yaml").read_text().replace("IMAGE_TO_RENDER", image))
