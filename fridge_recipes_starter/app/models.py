from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Text, ForeignKey, UniqueConstraint, Index

class Base(DeclarativeBase): ...

class Recipe(Base):
    __tablename__ = "recipes"
    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    title: Mapped[str] = mapped_column(String(300), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(500))
    prep_time_min: Mapped[int | None] = mapped_column(Integer)
    cuisine: Mapped[str | None] = mapped_column(String(80))
    source_url: Mapped[str | None] = mapped_column(String(500))
    ingredients: Mapped[list["RecipeIngredient"]] = relationship(back_populates="recipe", cascade="all, delete-orphan")
    tags: Mapped[list["RecipeTag"]] = relationship(back_populates="recipe", cascade="all, delete-orphan")
    __table_args__ = (Index("ix_recipe_cuisine_prep", "cuisine", "prep_time_min"),)

class Ingredient(Base):
    __tablename__ = "ingredients"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    normalized_name: Mapped[str] = mapped_column(String(200), unique=True, index=True)

class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id", ondelete="CASCADE"), primary_key=True)
    quantity: Mapped[str | None] = mapped_column(String(50))
    unit: Mapped[str | None] = mapped_column(String(50))
    raw_text: Mapped[str | None] = mapped_column(String(300))
    recipe: Mapped["Recipe"] = relationship(back_populates="ingredients")
    ingredient: Mapped["Ingredient"] = relationship()

class Tag(Base):
    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    normalized_name: Mapped[str] = mapped_column(String(100))
    type: Mapped[str | None] = mapped_column(String(40))
    __table_args__ = (UniqueConstraint("normalized_name", "type", name="uq_tag_norm_type"), Index("ix_tag_norm_type", "normalized_name", "type"))

class RecipeTag(Base):
    __tablename__ = "recipe_tags"
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
    recipe: Mapped["Recipe"] = relationship(back_populates="tags")
    tag: Mapped["Tag"] = relationship()

class Synonym(Base):
    __tablename__ = "synonyms"
    id: Mapped[int] = mapped_column(primary_key=True)
    term: Mapped[str] = mapped_column(String(200))
    normalized_term: Mapped[str] = mapped_column(String(200))

class YoloClassMap(Base):
    __tablename__ = "yolo_class_map"
    id: Mapped[int] = mapped_column(primary_key=True)
    yolo_label: Mapped[str] = mapped_column(String(100), unique=True)
    ingredient_normalized: Mapped[str] = mapped_column(String(200), index=True)

class Bookmark(Base):
    __tablename__ = "bookmarks"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str | None] = mapped_column(String(128))      # or auth user id
    device_key: Mapped[str | None] = mapped_column(String(128))   # or anon device id
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[Any] = mapped_column(DateTime(timezone=True), server_default=func.now())

    recipe: Mapped["Recipe"] = relationship()

    __table_args__ = (
        UniqueConstraint("user_id", "device_key", "recipe_id", name="uq_bookmark_owner_recipe"),
    )
