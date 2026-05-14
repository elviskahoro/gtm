"""ETL script for marketplace products.

This module parses marketplace_products.csv and converts each row into a Pydantic BaseModel.
Provides helper functions that can be called by other scripts.
"""

from pathlib import Path
from typing import Any

import polars as pl
from pydantic import BaseModel, Field


class MarketplaceProduct(BaseModel):
    """Pydantic model representing a marketplace product."""

    title: str = Field(
        description="Product title",
    )
    id: str = Field(
        description="Product ID",
    )
    product_category_id: str = Field(
        description="Product category UUID",
    )
    hid: int = Field(
        description="Product HID",
    )
    product_category_hid: int = Field(
        description="Product category HID",
    )
    description: str | None = None


def test_marketplace_product() -> None:
    """Test MarketplaceProduct model instantiation."""
    product = MarketplaceProduct(
        title="Gone Girl: A Novel",
        id="B006LSZECO",
        product_category_id="7c665b5f-eda4-4d57-a446-cba70e87f4cb",
        hid=333,
        product_category_hid=1,
    )

    assert product.title == "Gone Girl: A Novel"
    assert product.id == "B006LSZECO"
    assert product.hid == 333


def df_load_products(
    csv_path: str | Path,
) -> pl.DataFrame:
    """Load marketplace products from CSV into a Polars DataFrame.

    Args:
        csv_path: Path to the marketplace_products.csv file

    Returns:
        Polars DataFrame containing all products
    """
    df = pl.read_csv(
        source=csv_path,
    )

    return df


def test_df_load_products(tmp_path: Path) -> None:
    """Test loading products from CSV."""
    # Create a temporary CSV file
    csv_content = """title,id,product_category_id,hid,product_category_hid
Gone Girl: A Novel,B006LSZECO,7c665b5f-eda4-4d57-a446-cba70e87f4cb,333,1
Choke Point,B00AFPNV0,7c665b5f-eda4-4d57-a446-cba70e87f4cb,926,1"""

    csv_file = tmp_path / "test_products.csv"
    csv_file.write_text(csv_content)

    df = df_load_products(
        csv_path=csv_file,
    )

    assert df.shape[0] == 2
    assert df.shape[1] == 5
    assert "title" in df.columns


def parse_csv_row(
    row: dict[str, Any],
) -> MarketplaceProduct:
    """Parse a single CSV row into a MarketplaceProduct model.

    Args:
        row: Dictionary representing a single row from the CSV

    Returns:
        MarketplaceProduct instance
    """
    product = MarketplaceProduct(
        title=str(row["title"]),
        id=str(row["id"]),
        product_category_id=str(row["product_category_id"]),
        hid=int(row["hid"]),
        product_category_hid=int(row["product_category_hid"]),
    )

    return product


def test_parse_csv_row() -> None:
    """Test parsing a CSV row into a MarketplaceProduct."""
    row = {
        "title": "Gone Girl: A Novel",
        "id": "B006LSZECO",
        "product_category_id": "7c665b5f-eda4-4d57-a446-cba70e87f4cb",
        "hid": 333,
        "product_category_hid": 1,
    }

    product = parse_csv_row(
        row=row,
    )

    assert isinstance(product, MarketplaceProduct)
    assert product.title == "Gone Girl: A Novel"
    assert product.hid == 333


def load_products_as_models(
    csv_path: str | Path,
) -> list[MarketplaceProduct]:
    """Load all products from CSV as Pydantic models.

    Args:
        csv_path: Path to the marketplace_products.csv file

    Returns:
        List of MarketplaceProduct instances
    """
    df = df_load_products(
        csv_path=csv_path,
    )

    products = []

    for row_dict in df.to_dicts():
        product = parse_csv_row(
            row=row_dict,
        )
        products.append(product)

    return products


def test_load_products_as_models(tmp_path: Path) -> None:
    """Test loading products as Pydantic models."""
    csv_content = """title,id,product_category_id,hid,product_category_hid
Gone Girl: A Novel,B006LSZECO,7c665b5f-eda4-4d57-a446-cba70e87f4cb,333,1
Choke Point,B00AFPNV0,7c665b5f-eda4-4d57-a446-cba70e87f4cb,926,1"""

    csv_file = tmp_path / "test_products.csv"
    csv_file.write_text(csv_content)

    products = load_products_as_models(
        csv_path=csv_file,
    )

    assert len(products) == 2
    assert all(isinstance(p, MarketplaceProduct) for p in products)
    assert products[0].title == "Gone Girl: A Novel"


def get_products_by_category(
    csv_path: str | Path,
    category_id: str,
) -> list[MarketplaceProduct]:
    """Get all products belonging to a specific category.

    Args:
        csv_path: Path to the marketplace_products.csv file
        category_id: Product category UUID to filter by

    Returns:
        List of MarketplaceProduct instances matching the category
    """
    df = df_load_products(
        csv_path=csv_path,
    )

    filtered_df = df.filter(pl.col("product_category_id") == category_id)

    products = []

    for row_dict in filtered_df.to_dicts():
        product = parse_csv_row(
            row=row_dict,
        )
        products.append(product)

    return products


def test_get_products_by_category(tmp_path: Path) -> None:
    """Test filtering products by category."""
    csv_content = """title,id,product_category_id,hid,product_category_hid
Gone Girl: A Novel,B006LSZECO,7c665b5f-eda4-4d57-a446-cba70e87f4cb,333,1
Choke Point,B00AFPNV0,7c665b5f-eda4-4d57-a446-cba70e87f4cb,926,1
Other Product,B00OTHER,different-uuid,100,2"""

    csv_file = tmp_path / "test_products.csv"
    csv_file.write_text(csv_content)

    products = get_products_by_category(
        csv_path=csv_file,
        category_id="7c665b5f-eda4-4d57-a446-cba70e87f4cb",
    )

    assert len(products) == 2
    assert all(
        p.product_category_id == "7c665b5f-eda4-4d57-a446-cba70e87f4cb"
        for p in products
    )


def main() -> None:
    """Main execution function."""
    csv_path = (
        Path(__file__).parent.parent.parent.parent / "data" / "marketplace_products.csv"
    )

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found at {csv_path}")

    print(f"Loading products from {csv_path}")

    products = load_products_as_models(
        csv_path=csv_path,
    )
    print(f"Converted {len(products)} rows to MarketplaceProduct models")

    if products:
        print(f"\nFirst product: {products[0].title}")
        print(f"Product ID: {products[0].id}")
        print(f"Category ID: {products[0].product_category_id}")


if __name__ == "__main__":
    main()
