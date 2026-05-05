# trunk-ignore-all(pyright/reportUntypedFunctionDecorator)
"""Decode Gmail web URLs to API-usable message/thread IDs."""

import json
import shutil
import subprocess

import typer

from libs.gmail.url_decoder import decode_token, extract_id_from_url

app = typer.Typer(help="Gmail URL decoding.")


@app.command()
def decode(
    url_or_token: str = typer.Argument(help="A Gmail web URL or FMfcg... token"),
    read: bool = typer.Option(
        False,
        "--read",
        "-r",
        help="Fetch the message via gws after decoding",
    ),
) -> None:
    """Decode a Gmail URL or token to a hex API ID."""
    if url_or_token.startswith("http"):
        hex_id = extract_id_from_url(url_or_token)
    else:
        hex_id = decode_token(url_or_token)

    if not hex_id:
        typer.echo("Could not decode the provided URL or token.", err=True)
        raise typer.Exit(1)

    typer.echo(hex_id)

    if read:
        gws_path = shutil.which("gws")
        if not gws_path:
            typer.echo("gws not found on PATH.", err=True)
            raise typer.Exit(1)
        result = subprocess.run(
            [
                gws_path,
                "gmail",
                "users",
                "messages",
                "get",
                "--params",
                json.dumps(
                    {
                        "userId": "me",
                        "id": hex_id,
                        "format": "metadata",
                        "metadataHeaders": ["Subject", "From", "To", "Date"],
                    },
                ),
            ],
            capture_output=True,
            text=True,
        )
        typer.echo(result.stdout)
        if result.returncode != 0:
            typer.echo(result.stderr, err=True)
            raise typer.Exit(result.returncode)
