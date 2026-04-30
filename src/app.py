# trunk-ignore-all(pyright/reportUntypedFunctionDecorator)
import subprocess
import time
from datetime import UTC, datetime

import modal

from src.modal_app import MODAL_APP

# Force deployment with timestamp
_deploy_ts = time.time()
app = modal.App(name=MODAL_APP)


def _resolve_git_sha() -> str:
    try:
        out = subprocess.check_output(
            ["/usr/bin/git", "rev-parse", "--short", "HEAD"],
            text=True,
        )
        return out.strip() or "unknown"
    except Exception:
        return "unknown"


# HTTP endpoints with object-first naming (company_*, person_*, note_*)
# Deployment: 2026-03-29
image = (
    modal.Image.debian_slim(python_version="3.13")
    .pip_install(
        "attio>=0.21.2",
        "fastapi[standard]",
        "gtm-apollo>=0.0.2",
        "parallel-web",
        "pydantic>=2.0",
    )
    .env(
        {
            "AI_BUILD_GIT_SHA": _resolve_git_sha(),
            "AI_DEPLOYED_AT": datetime.now(UTC).isoformat(),
        }
    )
    .add_local_python_source("libs")
    .add_local_python_source("src")
)

secrets_apollo = modal.Secret.from_name("apollo")
secrets_attio = modal.Secret.from_name("attio")
secrets_parallel = modal.Secret.from_name("parallel")


import src.accounts.accounts as src_gtm_accounts  # noqa: E402
import src.accounts.batch as src_gtm_batch  # noqa: E402
import src.accounts.people as src_gtm_people  # noqa: E402
import src.accounts.research as src_gtm_research  # noqa: E402

# Import workflow modules so their @app.function / @modal.fastapi_endpoint
# decorators register with this app when Modal loads this file for deployment.
# NOTE: Free tier limit is 8 web endpoints. Parallel endpoints disabled until plan upgrade.
import src.apollo.organizations as src_apollo_organizations  # noqa: E402
import src.apollo.people as src_apollo_people  # noqa: E402
import src.attio.companies as src_attio_companies  # noqa: E402
import src.attio.notes as src_attio_notes  # noqa: E402
import src.attio.people as src_attio_people  # noqa: E402
import src.parallel.extract as src_parallel_extract  # noqa: E402
import src.parallel.findall as src_parallel_findall  # noqa: E402
import src.parallel.search as src_parallel_search  # noqa: E402

_ENDPOINT_MODULES = (
    src_apollo_organizations,
    src_apollo_people,
    src_attio_companies,
    src_attio_notes,
    src_attio_people,
    src_gtm_accounts,
    src_gtm_batch,
    src_gtm_people,
    src_gtm_research,
    src_parallel_extract,
    src_parallel_findall,
    src_parallel_search,
)
_REGISTERED_ENDPOINT_MODULES = _ENDPOINT_MODULES


@app.function(image=image)
def debug_ping() -> str:
    return "pong"
