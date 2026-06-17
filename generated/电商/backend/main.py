"""
Auto-generated E-commerce API
"""
import os
from datetime import datetime, timedelta
from typing import Optional
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3, json, hashlib, hmac, secrets

app = FastAPI(title="E-Commerce API", version="1.0.0", docs_url="/docs")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DB_PATH = os.environ.get("DB_PATH", "shop.db")
SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(32))

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            stock INTEGER DEFAULT 0,
            category TEXT,
            image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS cart_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            total REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id)
        );
    """)
    db.commit()
    # Seed products
    if not db.execute("SELECT COUNT(*) FROM products").fetchone()[0]:
        seed = [("无线蓝牙耳机","高品质降噪耳机",299,100,"电子产品"),
               ("机械键盘","青轴机械键盘",599,50,"电子产品"),
               ("纯棉T恤","舒适纯棉面料",129,200,"服装"),
               ("运动跑鞋","轻便透气跑鞋",399,80,"运动"),
               ("智能手表","多功能运动手表",899,30,"电子产品"),
               ("背包","大容量旅行背包",259,60,"箱包")]
        for n,d,p,s,c in seed:
            db.execute("INSERT INTO products(name,description,price,stock,category) VALUES(?,?,?,?,?)",(n,d,p,s,c))
        db.commit()

init_db()

# ── Models ──
class UserCreate(BaseModel):
    username: str; password: str; email: str = ""

class ProductOut(BaseModel):
    id: int; name: str; description: str; price: float; stock: int; category: str; image_url: str

class CartItemOut(BaseModel):
    id: int; product_id: int; name: str; price: float; quantity: int

class OrderCreate(BaseModel):
    address: str = ""

# ── Auth ──
def hash_pw(pw): return hashlib.sha256(f"{pw}:{SECRET_KEY}".encode()).hexdigest()
def create_token(uid): return hmac.new(SECRET_KEY.encode(), f"user:{uid}:{int(time.time())}".encode(), hashlib.sha256).hexdigest()

@app.post("/api/register")
def register(u: UserCreate):
    db = get_db()
    try:
        db.execute("INSERT INTO users(username,password_hash,email) VALUES(?,?,?)",(u.username,hash_pw(u.password),u.email))
        db.commit()
        return {"ok": True, "message": "注册成功"}
    except: raise HTTPException(400, "用户名已存在")

@app.post("/api/login")
def login(u: UserCreate):
    db = get_db()
    row = db.execute("SELECT id FROM users WHERE username=? AND password_hash=?",(u.username,hash_pw(u.password))).fetchone()
    if row: return {"ok": True, "token": create_token(row["id"]), "user_id": row["id"]}
    raise HTTPException(401, "用户名或密码错误")

# ── Products ──
@app.get("/api/products")
def list_products(category: str = "", search: str = ""):
    db = get_db()
    q = "SELECT * FROM products WHERE 1=1"
    p = []
    if category: q += " AND category=?"; p.append(category)
    if search: q += " AND (name LIKE ? OR description LIKE ?)"; p.append(f"%{search}%"); p.append(f"%{search}%")
    return {"ok": True, "products": [dict(r) for r in db.execute(q, p).fetchall()]}

@app.get("/api/products/{pid}")
def get_product(pid: int):
    db = get_db()
    r = db.execute("SELECT * FROM products WHERE id=?",(pid,)).fetchone()
    if r: return {"ok": True, "product": dict(r)}
    raise HTTPException(404, "商品不存在")

# ── Cart ──
@app.get("/api/cart/{uid}")
def get_cart(uid: int):
    db = get_db()
    items = db.execute("""
        SELECT ci.id, ci.product_id, p.name, p.price, ci.quantity
        FROM cart_items ci JOIN products p ON ci.product_id=p.id WHERE ci.user_id=?""",(uid,)).fetchall()
    return {"ok": True, "items": [dict(i) for i in items], "total": sum(i["price"]*i["quantity"] for i in items)}

@app.post("/api/cart/{uid}/add")
def add_to_cart(uid: int, pid: int, qty: int = 1):
    db = get_db()
    existing = db.execute("SELECT id,quantity FROM cart_items WHERE user_id=? AND product_id=?",(uid,pid)).fetchone()
    if existing:
        db.execute("UPDATE cart_items SET quantity=? WHERE id=?",(existing["quantity"]+qty,existing["id"]))
    else:
        db.execute("INSERT INTO cart_items(user_id,product_id,quantity) VALUES(?,?,?)",(uid,pid,qty))
    db.commit()
    return {"ok": True, "message": "已添加到购物车"}

@app.delete("/api/cart/{uid}/item/{item_id}")
def remove_cart_item(uid: int, item_id: int):
    get_db().execute("DELETE FROM cart_items WHERE id=? AND user_id=?",(item_id,uid)).connection.commit()
    return {"ok": True}

# ── Orders ──
@app.post("/api/orders/{uid}")
def create_order(uid: int, o: OrderCreate):
    db = get_db()
    items = db.execute("""
        SELECT ci.product_id, ci.quantity, p.price, p.name
        FROM cart_items ci JOIN products p ON ci.product_id=p.id WHERE ci.user_id=?""",(uid,)).fetchall()
    if not items: raise HTTPException(400, "购物车为空")
    total = sum(i["price"]*i["quantity"] for i in items)
    db.execute("INSERT INTO orders(user_id,total,address,status) VALUES(?,?,?,'paid')",(uid,total,o.address))
    oid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    for i in items:
        db.execute("INSERT INTO order_items(order_id,product_id,quantity,price) VALUES(?,?,?,?)",(oid,i["product_id"],i["quantity"],i["price"]))
        db.execute("UPDATE products SET stock=stock-? WHERE id=?",(i["quantity"],i["product_id"]))
    db.execute("DELETE FROM cart_items WHERE user_id=?",(uid,))
    db.commit()
    return {"ok": True, "order_id": oid, "total": total}

@app.get("/api/orders/{uid}")
def list_orders(uid: int):
    db = get_db()
    orders = db.execute("SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC",(uid,)).fetchall()
    result = []
    for o in orders:
        items = db.execute("SELECT oi.*,p.name FROM order_items oi JOIN products p ON oi.product_id=p.id WHERE oi.order_id=?",(o["id"],)).fetchall()
        result.append({**dict(o), "items": [dict(i) for i in items]})
    return {"ok": True, "orders": result}

@app.get("/api/admin/products")
def admin_products():
    db = get_db()
    return {"ok": True, "products": [dict(r) for r in db.execute("SELECT * FROM products ORDER BY id").fetchall()]}

@app.post("/api/admin/products")
def admin_create_product(name: str, price: float, description: str = "", stock: int = 0, category: str = ""):
    db = get_db()
    db.execute("INSERT INTO products(name,description,price,stock,category) VALUES(?,?,?,?,?)",(name,description,price,stock,category))
    db.commit()
    return {"ok": True, "message": "商品已添加"}

if __name__ == "__main__":
    import time; _ = time
    uvicorn.run(app, host="0.0.0.0", port=8000)
