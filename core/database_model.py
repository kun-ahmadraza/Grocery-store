from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    category_name = Column(String, unique=True)
    category_image = Column(String)

    orders = relationship("Order", back_populates="category")
    products = relationship("Product", back_populates="category")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    price = Column(Float)
    stock = Column(Integer)
    
    description = Column(String)
    category_name = Column(String, ForeignKey("categories.category_name"))
    category = relationship("Category", back_populates="products")

    images = relationship("Product_img", back_populates="product", cascade="all, delete")
    cart = relationship("Cart", back_populates="product")
    orders = relationship("Order", back_populates="product")

class Product_img(Base):
    __tablename__ = "product_img"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    image_url = Column(String)

    product = relationship("Product", back_populates="images")

class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String)
    password = Column(String)
    email = Column(String)
    role = Column(String, default="user")

    orders = relationship("Order", back_populates="user")

class Cart(Base):
    __tablename__ = "cart"

    cart_id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)
    user_id = Column(Integer, ForeignKey("user.id"))

    product = relationship("Product", back_populates="cart")

class Order(Base):
    __tablename__ = "order"

    order_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id")) 
    product_id = Column(Integer, ForeignKey("products.id"))   
    category_id = Column(Integer, ForeignKey("categories.id"))
    billing_id = Column(Integer, ForeignKey("billing_details.billing_id"))

    product = relationship("Product", back_populates="orders")
    user = relationship("User", back_populates="orders")
    category = relationship("Category", back_populates="orders")
    billing = relationship("Billing_details", back_populates="orders")

class Billing_details(Base):
    __tablename__ = "billing_details"

    billing_id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String)
    email = Column(String)
    phone = Column(String)
    country = Column(String)
    address = Column(String)
    city = Column(String)
    zip_code = Column(Integer)
    payment_method = Column(String)

    orders = relationship("Order", back_populates="billing")
