# trunk-ignore-all(ruff/PGH003,trunk/ignore-does-nothing)
from __future__ import annotations

from pathlib import Path

import modal
from modal import Image

from src.attio.export import execute

# trunk-ignore-begin(ruff/F401,ruff/I001,pyright/reportUnusedImport)
# fmt: off
from src.caldotcom.webhook.booking import (
    Webhook as CaldotcomBookingWebhook,
)
from src.fathom.webhook.call import (
    Webhook as FathomCallWebhook,
)
from src.fathom.webhook.message import (
    Webhook as FathomMessageWebhook,
)
from src.octolens.webhook import (
    Webhook as OctolensMentionWebhook,
)
from src.rb2b.webhook.visit import (
    Webhook as Rb2bVisitWebhook,
)

# fmt: on
# trunk-ignore-end(ruff/F401,ruff/I001,pyright/reportUnusedImport)

OctolensWebhook = OctolensMentionWebhook  # Backwards-compat alias for documented deploy flow

class WebhookModel(WebhookModelToReplace):  # type: ignore # trunk-ignore(ruff/F821)
    pass


WebhookModel.model_rebuild()

APP_NAME: str = WebhookModel.attio_get_app_name()

image: Image = modal.Image.debian_slim().uv_pip_install(
    "attio>=0.21.2",
    "fastapi[standard]",
    "flatsplode",
    "orjson",
    "uuid7",
)
image = image.add_local_python_source(
    *[
        "libs",
        "src",
    ],
)
app = modal.App(name=APP_NAME, image=image)


def _export(webhook: WebhookModel) -> str:
    if not webhook.attio_is_valid_webhook():
        return webhook.attio_get_invalid_webhook_error_msg()
    plan = webhook.attio_get_operations()
    return execute(plan).body()


@app.function(
    secrets=[
        modal.Secret.from_name(n)
        for n in WebhookModel.attio_get_secret_collection_names()
    ],
    region="us-east-1",
    enable_memory_snapshot=False,
)
@modal.fastapi_endpoint(method="POST", docs=True)
@modal.concurrent(max_inputs=1000)
def web(webhook: WebhookModel) -> str:
    return _export(webhook)


@app.local_entrypoint()
def local(input_file: str) -> None:
    import orjson

    raw = Path(input_file).read_bytes()
    payload = orjson.loads(raw)
    webhook = WebhookModel.model_validate(payload)
    print(_export(webhook))
