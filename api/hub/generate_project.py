"""
AUTO-EVO-AI 项目生成器 — 智能生成完整项目代码
支持: ecommerce, blog, crm, dashboard, api, webapp
"""
import logging
logger = logging.getLogger("evo.generate_project")

import os, json, subprocess, time, shutil, re
from pathlib import Path

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEMPLATES = {
    "ecommerce": {
        "name": "电商网站",
        "description": "完整电商系统：商品管理/购物车/订单/支付",
        "services": ["mysql:8.0", "redis:7"],
    },
    "blog": {
        "name": "博客系统",
        "description": "Markdown博客：文章/分类/标签/评论",
        "services": ["mysql:8.0"],
    },
    "crm": {
        "name": "客户管理系统",
        "description": "CRM：客户/商机/合同/报表",
        "services": ["mysql:8.0", "redis:7"],
    },
    "dashboard": {
        "name": "数据仪表盘",
        "description": "BI仪表盘：图表/看板/KPI监控",
        "services": ["mysql:8.0"],
    },
    "api": {
        "name": "REST API服务",
        "description": "FastAPI RESTful 后端服务",
        "services": ["mysql:8.0"],
    },
    "webapp": {
        "name": "Web应用",
        "description": "Vue + FastAPI 全栈应用",
        "services": ["mysql:8.0"],
    },
}

# ── E-commerce backend code ──

ECOMMERCE_BACKEND = r'''"""
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
'''

ECOMMERCE_FRONTEND = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>电商网站</title>
<script src="https://unpkg.com/vue@3/dist/vue.global.prod.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
body{background:#f5f5f5}
.header{background:#1a1a2e;color:white;padding:16px 32px;display:flex;justify-content:space-between;align-items:center}
.header h1{font-size:20px}
.nav{display:flex;gap:16px}
.nav a{color:#ccc;cursor:pointer;text-decoration:none;padding:4px 12px;border-radius:4px}
.nav a:hover,.nav a.active{color:white;background:rgba(255,255,255,.1)}
.container{max-width:1200px;margin:0 auto;padding:24px 16px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:16px}
.card{background:white;border-radius:12px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,.08);cursor:pointer;transition:transform .2s}
.card:hover{transform:translateY(-4px);box-shadow:0 4px 16px rgba(0,0,0,.12)}
.card h3{font-size:16px;margin-bottom:8px}
.card .price{color:#e44;font-size:20px;font-weight:bold}
.card .stock{color:#999;font-size:12px;margin-top:4px}
.card .desc{color:#666;font-size:13px;margin:8px 0;line-height:1.4}
.btn{background:#1a1a2e;color:white;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;font-size:14px}
.btn:hover{background:#16213e}.btn-sm{padding:4px 12px;font-size:12px}
.cart{position:fixed;top:0;right:0;width:380px;height:100vh;background:white;box-shadow:-4px 0 20px rgba(0,0,0,.15);padding:20px;overflow-y:auto;z-index:100}
.cart h2{margin-bottom:16px}.cart-item{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #eee}
.cart-total{margin-top:16px;font-size:18px;font-weight:bold;text-align:right}
.overlay{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.3);z-index:99}
.auth-form{max-width:360px;margin:40px auto;background:white;padding:32px;border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,.1)}
.auth-form h2{text-align:center;margin-bottom:20px}
.auth-form input{width:100%;padding:10px;margin-bottom:12px;border:1px solid #ddd;border-radius:6px;font-size:14px}
.auth-form .btn{width:100%;margin-top:8px}
.notice{position:fixed;top:20px;left:50%;transform:translateX(-50%);background:#4caf50;color:white;padding:12px 24px;border-radius:8px;z-index:200;animation:fadeIn .3s}
@keyframes fadeIn{from{opacity:0;top:0}to{opacity:1;top:20px}}
</style></head>
<body>
<div id="app">
  <div class="header">
    <h1>{{ storeName }}</h1>
    <div class="nav">
      <a :class="{active:page=='shop'}" @click="page='shop'">商店</a>
      <a :class="{active:page=='orders'}" @click="fetchOrders();page='orders'" v-if="token">订单</a>
      <a @click="showCart=!showCart">购物车({{ cartCount }})</a>
      <a @click="loginPage=!loginPage" v-if="!token">登录</a>
      <a @click="logout()" v-if="token">退出({{ username }})</a>
    </div>
  </div>

  <div class="container" v-if="page=='shop'">
    <div style="display:flex;gap:12px;margin-bottom:20px;flex-wrap:wrap">
      <input v-model="search" placeholder="搜索商品..." style="padding:8px 12px;border:1px solid #ddd;border-radius:6px;flex:1;min-width:200px">
      <select v-model="category" style="padding:8px 12px;border:1px solid #ddd;border-radius:6px">
        <option value="">全部分类</option>
        <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
      </select>
    </div>
    <div class="grid">
      <div class="card" v-for="p in filteredProducts" :key="p.id" @click="addToCart(p)">
        <h3>{{ p.name }}</h3>
        <div class="price">&yen;{{ p.price.toFixed(2) }}</div>
        <div class="desc">{{ p.description }}</div>
        <div class="stock">库存: {{ p.stock }}</div>
        <button class="btn btn-sm" style="margin-top:8px" @click.stop="addToCart(p)">加入购物车</button>
      </div>
    </div>
    <p v-if="filteredProducts.length==0" style="text-align:center;color:#999;margin-top:40px">暂无商品</p>
  </div>

  <div class="container" v-if="page=='orders'">
    <h2 style="margin-bottom:16px">我的订单</h2>
    <div v-for="o in orders" :key="o.id" style="background:white;border-radius:8px;padding:16px;margin-bottom:12px;box-shadow:0 1px 4px rgba(0,0,0,.08)">
      <div style="display:flex;justify-content:space-between;margin-bottom:8px">
        <strong>订单 #{{ o.id }}</strong>
        <span :style="{color:o.status=='paid'?'green':'orange'}">{{ o.status=='paid'?'已支付':'待处理' }}</span>
      </div>
      <div v-for="i in (o.items||[])" :key="i.id" style="display:flex;justify-content:space-between;font-size:14px;color:#666;padding:4px 0">
        <span>{{ i.name }} x{{ i.quantity }}</span>
        <span>&yen;{{ (i.price*i.quantity).toFixed(2) }}</span>
      </div>
      <div style="text-align:right;margin-top:8px;font-weight:bold">合计: &yen;{{ o.total.toFixed(2) }}</div>
    </div>
  </div>

  <div class="overlay" v-if="showCart" @click="showCart=false"></div>
  <div class="cart" v-if="showCart">
    <h2>购物车</h2>
    <div v-for="(item,idx) in cart" :key="idx" class="cart-item">
      <div><strong>{{ item.name }}</strong><br><span style="color:#999;font-size:12px">&yen;{{ item.price }}</span></div>
      <div style="display:flex;align-items:center;gap:8px">
        <button class="btn btn-sm" @click="updateQty(idx,-1)">-</button>
        {{ item.qty }}
        <button class="btn btn-sm" @click="updateQty(idx,1)">+</button>
        <button class="btn btn-sm" style="background:#e44" @click="removeItem(idx)">删除</button>
      </div>
    </div>
    <div v-if="cart.length==0" style="text-align:center;color:#999;margin-top:40px">购物车为空</div>
    <div class="cart-total" v-if="cart.length">合计: &yen;{{ cartTotal.toFixed(2) }}</div>
    <button class="btn" style="width:100%;margin-top:16px" @click="checkout()" v-if="cart.length&&token">结算</button>
    <p v-if="cart.length&&!token" style="text-align:center;color:#e44;margin-top:8px;font-size:13px">请先登录再结算</p>
  </div>

  <div class="overlay" v-if="loginPage" @click="loginPage=false"></div>
  <div class="auth-form" v-if="loginPage" style="position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:101;width:340px">
    <h2>{{ isRegister ? '注册' : '登录' }}</h2>
    <input v-model="authUser" placeholder="用户名">
    <input v-model="authPass" type="password" placeholder="密码">
    <input v-model="authEmail" placeholder="邮箱(选填)" v-if="isRegister">
    <button class="btn" @click="doAuth()">{{ isRegister ? '注册' : '登录' }}</button>
    <p style="text-align:center;margin-top:12px;font-size:13px;color:#666">
      <a @click="isRegister=!isRegister" style="cursor:pointer;color:#1a1a2e">{{ isRegister ? '已有账号？去登录' : '没有账号？去注册' }}</a>
    </p>
    <p v-if="demoAccount" style="text-align:center;margin-top:8px;font-size:12px;color:#999">测试账号: demo / demo123</p>
  </div>

  <div class="notice" v-if="notice">{{ notice }}</div>
</div>

<script>
const { createApp, ref, computed, onMounted } = Vue;
createApp({
  setup() {
    const API = window.location.origin;
    const page = ref('shop');
    const products = ref([]); const cart = ref([]); const orders = ref([]);
    const search = ref(''); const category = ref('');
    const showCart = ref(false); const loginPage = ref(false); const isRegister = ref(false);
    const token = ref(localStorage.getItem('token')||'');
    const username = ref(localStorage.getItem('username')||'demo');
    const authUser = ref(''); const authPass = ref(''); const authEmail = ref('');
    const notice = ref(''); const storeName = ref('我的商店');
    const demoAccount = ref(true);
    const userId = ref(parseInt(localStorage.getItem('user_id')||'1'));

    const categories = computed(() => [...new Set(products.value.map(p=>p.category).filter(Boolean))]);

    const filteredProducts = computed(() => products.value.filter(p => {
      if(category.value && p.category!=category.value) return false;
      if(search.value && !p.name.toLowerCase().includes(search.value.toLowerCase()) && !(p.description||'').toLowerCase().includes(search.value.toLowerCase())) return false;
      return true;
    }));

    const cartItems = computed(() => cart.value);
    const cartTotal = computed(() => cart.value.reduce((s,i)=>s+i.price*i.qty,0));
    const cartCount = computed(() => cart.value.reduce((s,i)=>s+i.qty,0));

    function showNotice(msg){notice.value=msg;setTimeout(()=>notice.value='',2000)}

    async function api(path, opts={}){
      try{
        const r = await fetch(API+path, {headers:{'Content-Type':'application/json',...opts.headers}, ...opts});
        return await r.json();
      }catch(e){return {ok:false,message:e.message}}
    }

    async function fetchProducts(){
      const q = new URLSearchParams(); if(category.value) q.set('category',category.value); if(search.value) q.set('search',search.value);
      const r = await api('/api/products?'+q.toString()); if(r.ok) products.value=r.products;
    }

    async function addToCart(p){
      if(!token.value){loginPage.value=true;return}
      const r = await api(`/api/cart/${userId.value}/add?pid=${p.id}&qty=1`,{method:'POST'});
      if(r.ok){showNotice('已添加到购物车');fetchCart()}
    }

    async function fetchCart(){
      const r = await api(`/api/cart/${userId.value}`); if(r.ok) cart.value=r.items.map(i=>({...i,qty:i.quantity}));
    }

    async function updateQty(idx,delta){
      const item = cart.value[idx]; const newQty = item.qty+delta;
      if(newQty<=0){cart.value.splice(idx,1);return}
      await api(`/api/cart/${userId.value}/add?pid=${item.product_id}&qty=${delta}`,{method:'POST'});
      item.qty=newQty;
    }

    function removeItem(idx){cart.value.splice(idx,1)}

    async function checkout(){
      const r = await api(`/api/orders/${userId.value}`,{method:'POST',body:JSON.stringify({address:''})});
      if(r.ok){showNotice('下单成功！');cart.value=[];showCart.value=false;fetchOrders()}
    }

    async function fetchOrders(){
      const r = await api(`/api/orders/${userId.value}`); if(r.ok) orders.value=r.orders;
    }

    async function doAuth(){
      const ep = isRegister.value ? '/api/register' : '/api/login';
      const r = await api(ep, {method:'POST',body:JSON.stringify({username:authUser.value||'demo',password:authPass.value||'demo123',email:authEmail.value})});
      if(r.ok){
        if(r.token){token.value=r.token;userId.value=r.user_id||1;localStorage.setItem('token',r.token);localStorage.setItem('user_id',userId.value);localStorage.setItem('username',authUser.value||'demo')}
        showNotice(isRegister.value?'注册成功':'登录成功');loginPage.value=false;fetchCart()
      } else showNotice(r.detail||'操作失败');
    }

    function logout(){token.value='';localStorage.removeItem('token');page.value='shop';cart.value=[]}

    onMounted(()=>{fetchProducts()});
    return {page,products,orders,cart,search,category,categories,filteredProducts,showCart,loginPage,isRegister,token,username,authUser,authPass,authEmail,notice,storeName,demoAccount,userId,cartItems,cartTotal,cartCount,fetchProducts,addToCart,fetchCart,updateQty,removeItem,checkout,fetchOrders,doAuth,logout}
  }
}).mount('#app');
</script></body></html>
'''

ECOMMERCE_DOCKER_COMPOSE = '''version: "3.8"
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DB_PATH=/data/shop.db
      - SECRET_KEY=change_this_secret_key_in_production
    volumes:
      - shop_data:/data
    depends_on:
      mysql:
        condition: service_healthy
  frontend:
    image: nginx:alpine
    ports:
      - "8080:80"
    volumes:
      - ./frontend:/usr/share/nginx/html:ro
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_DATABASE: shop
      MYSQL_USER: shop
      MYSQL_PASSWORD: shoppass
    ports:
      - "3307:3306"
    healthcheck:
      test: ["CMD","mysqladmin","ping","-h","localhost"]
      interval: 5s
      timeout: 3s
      retries: 10
    volumes:
      - mysql_data:/var/lib/mysql
  redis:
    image: redis:7
    ports:
      - "6380:6379"
volumes:
  shop_data:
  mysql_data:
'''

class ProjectGenerator:
    def __init__(self):
        self.base = BASE

    def generate(self, project_type: str, name: str) -> dict:
        if project_type not in TEMPLATES:
            return {"ok": False, "message": f"不支持的项目类型: {project_type}，支持: {list(TEMPLATES.keys())}"}

        template = TEMPLATES[project_type]
        out_dir = os.path.join(self.base, "generated", name)
        os.makedirs(os.path.join(out_dir, "backend"), exist_ok=True)
        os.makedirs(os.path.join(out_dir, "frontend"), exist_ok=True)

        files_created = []

        # Backend
        if project_type == "ecommerce":
            with open(os.path.join(out_dir, "backend", "main.py"), "w", encoding="utf-8") as f:
                f.write(ECOMMERCE_BACKEND)
            files_created.append("backend/main.py")
            with open(os.path.join(out_dir, "backend", "requirements.txt"), "w") as f:
                f.write("fastapi\nuvicorn\npydantic\n")
            files_created.append("backend/requirements.txt")
            with open(os.path.join(out_dir, "backend", "Dockerfile"), "w") as f:
                f.write("FROM python:3.11-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install -r requirements.txt\nCOPY . .\nCMD [\"python\", \"main.py\"]\n")
            files_created.append("backend/Dockerfile")
            # Frontend
            with open(os.path.join(out_dir, "frontend", "index.html"), "w", encoding="utf-8") as f:
                f.write(ECOMMERCE_FRONTEND)
            files_created.append("frontend/index.html")
            # Docker Compose
            with open(os.path.join(out_dir, "docker-compose.yml"), "w") as f:
                f.write(ECOMMERCE_DOCKER_COMPOSE)
            files_created.append("docker-compose.yml")
        else:
            # Generic template for other project types
            with open(os.path.join(out_dir, "backend", "main.py"), "w") as f:
                f.write(f'''"""
{template["name"]} — Auto-generated by AUTO-EVO-AI
"""
from fastapi import FastAPI
app = FastAPI(title="{template["name"]}", version="1.0.0")
@app.get("/")
def root():
    return {{"ok": True, "name": "{template["name"]}", "services": {json.dumps(template["services"])}}}
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
''')
            files_created.append("backend/main.py")
            with open(os.path.join(out_dir, "backend", "requirements.txt"), "w") as f:
                f.write("fastapi\nuvicorn\n")
            files_created.append("backend/requirements.txt")
            with open(os.path.join(out_dir, "frontend", "index.html"), "w") as f:
                f.write(f"<h1>{template['name']}</h1><p>{template['description']}</p>")
            files_created.append("frontend/index.html")

        # README
        services_str = ", ".join(template["services"])
        with open(os.path.join(out_dir, "README.md"), "w", encoding="utf-8") as f:
            f.write(f"# {name}\n\n## {template['name']}\n{template['description']}\n\n## 依赖服务\n{services_str}\n\n## 启动\n```bash\ndocker-compose up -d\n```\n")
        files_created.append("README.md")

        return {"ok": True, "path": out_dir, "message": f"{template['name']} 项目已生成到 {out_dir}", "files_count": len(files_created), "files": files_created, "services": template["services"]}

    def list_types(self) -> list:
        return [{"id": k, "name": v["name"], "description": v["description"], "services": v["services"]} for k, v in TEMPLATES.items()]
