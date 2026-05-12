# trunk-ignore-all(ruff/PGH003,trunk/ignore-does-nothing)
from __future__ import annotations

from pathlib import Path

import modal
from modal import Image

# trunk-ignore-begin(ruff/F401,ruff/I001,pyright/reportUnusedImport)
# fmt: off
from src.fathom.webhook.message import (
    Webhook as FathomMessageWebhook,
)
from src.fathom.webhook.call import (
    Webhook as FathomCallWebhook,
)
from src.octolens.webhook import (
    Webhook as OctolensWebhook,
)
from src.rb2b.webhook.visit import (
    Webhook as Rb2bVisitWebhook,
)
from src.caldotcom.webhook.booking import (
    Webhook as CaldotcomBookingWebhook,
)
# fmt: on
# trunk-ignore-end(ruff/F401,ruff/I001,pyright/reportUnusedImport)

from src.attio.export import execute


class WebhookModel(FathomCallWebhook):  # type: ignore # trunk-ignore(ruff/F821)
    pass


WebhookModel.model_rebuild()


image: Image = modal.Image.debian_slim().uv_pip_install(
    "attio>=0.21.2",
    "fastapi[standard]",
    "orjson",
    "uuid7",
)
image = image.add_local_python_source(
    *[
        "libs",
        "src",
    ],
)
app = modal.App(name="export-to-attio", image=image)


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
