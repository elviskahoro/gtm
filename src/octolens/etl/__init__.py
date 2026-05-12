"""Octolens ETL contract — re-exports the active mention webhook."""

from src.octolens.etl.mention import Webhook

__all__ = ["Webhook"]
