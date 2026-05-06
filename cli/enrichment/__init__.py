import typer

from cli.enrichment.enrich import app as enrich_app

app = typer.Typer(help="LinkedIn enrichment commands.")

app.add_typer(enrich_app, name="enrich")
