from fastapi import FastAPI, Request, Form, File, UploadFile, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from core import database_model 
from core.config import engine, get_db
from sqlalchemy.orm import Session
import os, shutil
from typing import List
from starlette.middleware.base import BaseHTTPMiddleware
from core.auth import hash_password, verify_password, create_token, get_current_user

class CurrentUserMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.current_user = get_current_user(request)
        return await call_next(request)

app = FastAPI()

app.add_middleware(CurrentUserMiddleware)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# Pass current_user function to templates
def current_user(request):
    return request.state.current_user

templates.env.globals["current_user"] = current_user

database_model.Base.metadata.create_all(bind=engine)

@app.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    db: Session = Depends(get_db)
    ):
    category = db.query(database_model.Category).all()
    
    return templates.TemplateResponse("index.html", {"request":request,"category":category})

@app.get("/cart", response_class=HTMLResponse)
async def cart(request: Request, db: Session = Depends(get_db)):
    cart = db.query(database_model.Cart).all()

    for item in cart:
        item.subtotal = item.quantity * item.product.price

    total = sum(item.subtotal for item in cart)

    return templates.TemplateResponse("cart.html", {"request":request, "cart":cart, "total": total})

@app.post("/update_quantity/{cart_id}")
def update_quantity(cart_id: int, action: str, db: Session = Depends(get_db)):

    cart_item = db.query(database_model.Cart).filter_by(cart_id=cart_id).first()
    if not cart_item:
        return {"success": False}

    if action == "increase":
        cart_item.quantity += 1
    elif action == "decrease" and cart_item.quantity > 1:
        cart_item.quantity -= 1

    db.commit()

    return {"success": True, "new_quantity": cart_item.quantity}

@app.get("/Add_product", response_class=HTMLResponse)
def Add_product_form(request: Request, db: Session = Depends(get_db)):
    categories = db.query(database_model.Category).all()
    return templates.TemplateResponse("add_product.html", {
        "request": request,
        "categories": categories
    })

@app.post("/Add_product", response_class=HTMLResponse)
async def Add_product(
    request: Request,
    name: str = Form(...),
    price : float = Form(...),
    stock : int = Form(...),
    description : str = Form(None),
    category_name : str = Form(...),
    images : List[UploadFile] = File(...),
    db : Session = Depends(get_db)
    ):

    new_product = database_model.Product(
        name=name,
        price=price,
        stock=stock,
        description=description,
        category_name=category_name
    )
    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    os.makedirs("static/uploads", exist_ok=True)
    saved_files = []
    for image in images:
        filename = image.filename
        filepath = f"static/uploads/{filename}"

        with open(filepath, "wb")as buffer:
            shutil.copyfileobj(image.file, buffer)

        product_img = database_model.Product_img(
            image_url=filepath,
            product_id = new_product.id,
        )
        db.add(product_img)
        saved_files.append(filename)

    db.commit()

    categories = db.query(database_model.Category).all()

    return templates.TemplateResponse("add_product.html", {
        "request":request,
        "product":new_product,
        "images":saved_files,
        "success":True,
        "categories":categories
    })

@app.post("/add-category", response_class=HTMLResponse)
async def Add_category(
    db: Session = Depends(get_db),
    category_name: str = Form(...),
    category_image: UploadFile = File(...)
    ):

    os.makedirs("static/uploads/category", exist_ok=True)

    filename = category_image.filename
    filepath = f"static/uploads/category/{filename}"

    with open(filepath, "wb")as buffer:
        shutil.copyfileobj(category_image.file, buffer)

    new_cat = database_model.Category(
        category_name = category_name,
        category_image = f"/static/uploads/category/{filename}"

    )
    db.add(new_cat)
    db.commit()
    db.refresh(new_cat)

    return RedirectResponse(url="/Add_product", status_code=303)

@app.get("/dashboard", response_class=HTMLResponse)
async def dasboard(request:Request, db:Session=Depends(get_db)):
    products = db.query(database_model.Product).all()
    image = db.query(database_model.Product_img).all()
    return templates.TemplateResponse("dashboard.html", {
        "request":request,
        "products":products,
        "image":image
    })


@app.post("/delete_product/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(database_model.Product).filter(database_model.Product.id == product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")


    # Delete product images first (if your model has relationship)
    for img in product.images:
        db.delete(img)

    # Then delete the product
    db.delete(product)
    db.commit()

    # Redirect back to dashboard
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/checkout", response_class=HTMLResponse)
async def checkout(request:Request):
    return templates.TemplateResponse("checkout.html", {"request":request})

@app.get("/category/{cat_name}", response_class=HTMLResponse)
async def category_products(
    cat_name : str,
    request:Request,
    db: Session = Depends(get_db),
    ):
    category = db.query(database_model.Category).filter(database_model.Category.category_name == cat_name).first()

    if not category:
        return HTMLResponse("Category Not Found", status_code=404)
    
    products = db.query(database_model.Product).filter(database_model.Product.category_name == cat_name).all()

    return templates.TemplateResponse("cat_products.html", {"request":request, "category":category, "products":products})

@app.post("/add_to_cart")
async def add_to_cart(
    product_id: int = Form(...),
    quantity: int = Form(1),
    request: Request = None,
    db: Session = Depends(get_db)
    ):

    user = get_current_user(request)

    if not user:
        return RedirectResponse(url="/log-in", status_code=303)
    
    user_id = user["user_id"]

    existing_item = db.query(database_model.Cart).filter(
        database_model.Cart.product_id == product_id,
        database_model.Cart.user_id == user_id).first()

    if existing_item:
        existing_item.quantity += quantity
    else:
        new_item = database_model.Cart(product_id=product_id, quantity=quantity, user_id=user_id)
        db.add(new_item)

    db.commit()

    return RedirectResponse(url="/cart", status_code=303)

@app.get("/sign-up", response_class=HTMLResponse)
async def signup(request:Request):
    return templates.TemplateResponse("signup.html", {"request":request})

@app.post("/sign-up",response_class=HTMLResponse)
async def signup(
    username:str = Form(...), 
    email: str = Form(...), 
    password: str = Form(...), 
    role : str = Form('user'),
    db : Session = Depends(get_db)
    ):
    password = hash_password(password)
    
    new_user = database_model.User(
        username = username,
        email= email,
        password = password,
        role = role
    )
    db.add(new_user)
    db.commit()
    
    return RedirectResponse(url="/log-in", status_code=303)


@app.get("/log-in",response_class=HTMLResponse)
async def login(
    request:Request
    ):
    return templates.TemplateResponse("login.html", {"request":request})

@app.post("/log-in", response_class=HTMLResponse)
async def login(
    request:Request,
    email: str =Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
    ):
    user = db.query(database_model.User).filter(database_model.User.email == email).first()


    if not user or not verify_password(password, user.password):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid email or password"
        })
    
    token = create_token({"user_id":user.id, "user_role":user.role, "username":user.username})

    response = RedirectResponse("/", status_code=302)
    response.set_cookie(key="auth", value=token, httponly=True)

    return response

@app.post("/Buy-Now", response_class=HTMLResponse)
async def buy_now(
    request:Request, 
    product_id: int = Form(...), 
    quantity: int = Form(1), 
    db : Session = Depends(get_db)
    ):
    product = db.query(database_model.Product).filter(database_model.Product.id == product_id).first()

    user = get_current_user(request)
    user_id = user['user_id']

    User = db.query(database_model.User).filter(database_model.User.id == user_id).first()

    if not user:
        return RedirectResponse(url="/log-in", status_code=303)

    if not product:
        raise HTTPException(status_code=404, detail="Product Not Found")
    
    total = product.price * quantity

    return templates.TemplateResponse("checkout.html", {"request":request, "product": product, "quantity":quantity, "total":total, "User":User})


@app.post("/place_order", response_class=HTMLResponse)
async def place_order(
    request:Request,
    phone : str = Form(...),
    address : str = Form(...),
    city : str = Form(...),
    country: str = Form(...),
    zip_code : int = Form(...),
    payment_method : str = Form(...),
    db : Session = Depends(get_db) 
    ):

    user = get_current_user(request)

    user_id = user['user_id']

    user = db.query(database_model.User).filter(database_model.User.id == user_id).first()

    full_name = user.username
    email = user.email

    billing_details = database_model.Billing_details(
        full_name = full_name,
        email=email,
        phone = phone,
        country = country,
        address = address,
        city = city,
        zip_code = zip_code
    )

    db.add(billing_details)
    db.commit()

    return templates.TemplateResponse("confirm.html", {
        "request":request,
        "full_name":full_name,
        "email":email,
        "phone":phone,
        "country":country,
        "address":address,
        "city":city,
        "zip_code":zip_code,
        "payment_method":payment_method
        })