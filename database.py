from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

SERVICE_ACCOUNT = "serviceAccountKey.json"

if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_ACCOUNT)
    firebase_admin.initialize_app(cred)

db = firestore.client()


def now():
    return datetime.utcnow().isoformat()


def init_db():
    # Firebase no necesita crear tablas.
    return True


def user_ref(telegram_id):
    return db.collection("users").document(str(telegram_id))


def get_or_create_user(tg_user, ref_id=None):
    ref = user_ref(tg_user.id)
    snap = ref.get()

    if not snap.exists:
        invited_by = ref_id if ref_id and ref_id != tg_user.id else None

        ref.set({
            "telegram_id": tg_user.id,
            "username": tg_user.username,
            "first_name": tg_user.first_name,
            "balance": 0.0,
            "invited_by": invited_by,
            "created_at": now()
        })

        if invited_by:
            user_ref(invited_by).set({
                "telegram_id": invited_by,
                "balance": firestore.Increment(0.25)
            }, merge=True)

    return get_user(tg_user.id)


def get_user(telegram_id):
    snap = user_ref(telegram_id).get()
    if not snap.exists:
        return None

    u = snap.to_dict()
    return (
        u.get("telegram_id"),
        u.get("username"),
        u.get("first_name"),
        float(u.get("balance", 0)),
        u.get("invited_by"),
        u.get("created_at")
    )


def add_balance(telegram_id, amount):
    ref = user_ref(telegram_id)

    if not ref.get().exists:
        return False

    ref.update({
        "balance": firestore.Increment(float(amount))
    })

    return True


def add_product(name, price, items):
    product_ref = db.collection("products").document()
    product_id = product_ref.id

    product_ref.set({
        "id": product_id,
        "name": name,
        "price": float(price),
        "active": 1,
        "created_at": now()
    })

    for item in items:
        item = item.strip()
        if item:
            db.collection("stock").document().set({
                "product_id": product_id,
                "item": item,
                "sold": 0,
                "created_at": now()
            })

    return product_id


def get_products():
    products = db.collection("products").where("active", "==", 1).stream()

    rows = []

    for p in products:
        data = p.to_dict()
        product_id = data.get("id", p.id)

        stock = db.collection("stock") \
            .where("product_id", "==", product_id) \
            .where("sold", "==", 0) \
            .stream()

        available = sum(1 for _ in stock)

        rows.append((
            product_id,
            data.get("name"),
            float(data.get("price", 0)),
            available
        ))

    rows.sort(key=lambda x: str(x[0]), reverse=True)
    return rows


@firestore.transactional
def _buy_transaction(transaction, telegram_id, product_id):
    product_ref = db.collection("products").document(str(product_id))
    user = user_ref(telegram_id)

    product_snap = product_ref.get(transaction=transaction)
    user_snap = user.get(transaction=transaction)

    if not product_snap.exists:
        return False, "Producto no disponible."

    product = product_snap.to_dict()

    if product.get("active") != 1:
        return False, "Producto no disponible."

    if not user_snap.exists:
        return False, "Usuario no encontrado."

    user_data = user_snap.to_dict()
    balance = float(user_data.get("balance", 0))

    try:
        price = float(product.get("price"))
    except Exception:
        return False, "El producto no tiene precio válido."

    if price <= 0:
        return False, "El producto tiene precio inválido."

    if balance < price:
        return False, f"Saldo insuficiente. Necesitas ${price:.2f} USD."

    stock_query = db.collection("stock") \
        .where("product_id", "==", str(product_id)) \
        .where("sold", "==", 0) \
        .limit(1)

    stock_docs = list(stock_query.stream(transaction=transaction))

    if not stock_docs:
        return False, "No hay stock disponible."

    stock_doc = stock_docs[0]
    stock_data = stock_doc.to_dict()
    item = stock_data.get("item")

    transaction.update(user, {
        "balance": firestore.Increment(-price)
    })

    transaction.update(stock_doc.reference, {
        "sold": 1,
        "sold_at": now()
    })

    purchase_ref = db.collection("purchases").document()
    transaction.set(purchase_ref, {
        "telegram_id": telegram_id,
        "product_id": str(product_id),
        "product_name": product.get("name"),
        "price": price,
        "item": item,
        "created_at": now()
    })

    return True, item


def buy_product(telegram_id, product_id):
    transaction = db.transaction()
    return _buy_transaction(transaction, telegram_id, product_id)


def add_coupon(code, amount, max_uses):
    code = code.upper().strip()

    ref = db.collection("coupons").document(code)
    snap = ref.get()

    used_count = 0
    if snap.exists:
        used_count = snap.to_dict().get("used_count", 0)

    ref.set({
        "code": code,
        "amount": float(amount),
        "max_uses": int(max_uses),
        "used_count": used_count,
        "active": 1,
        "created_at": now()
    }, merge=True)


@firestore.transactional
def _redeem_transaction(transaction, telegram_id, code):
    coupon_ref = db.collection("coupons").document(code)
    use_ref = db.collection("coupon_uses").document(f"{code}_{telegram_id}")
    user = user_ref(telegram_id)

    coupon_snap = coupon_ref.get(transaction=transaction)
    use_snap = use_ref.get(transaction=transaction)

    if not coupon_snap.exists:
        return False, "Cupón inválido."

    coupon = coupon_snap.to_dict()

    if coupon.get("active") != 1 or coupon.get("used_count", 0) >= coupon.get("max_uses", 0):
        return False, "Cupón agotado o inactivo."

    if use_snap.exists:
        return False, "Ya usaste este cupón."

    amount = float(coupon.get("amount", 0))

    transaction.set(use_ref, {
        "code": code,
        "telegram_id": telegram_id,
        "used_at": now()
    })

    transaction.update(coupon_ref, {
        "used_count": firestore.Increment(1)
    })

    transaction.set(user, {
        "telegram_id": telegram_id,
        "balance": firestore.Increment(amount)
    }, merge=True)

    return True, f"Cupón aplicado. Se agregaron ${amount:.2f} USD."


def redeem_coupon(telegram_id, code):
    code = code.upper().strip()
    transaction = db.transaction()
    return _redeem_transaction(transaction, telegram_id, code)


def get_purchases(telegram_id):
    docs = db.collection("purchases") \
        .where("telegram_id", "==", telegram_id) \
        .stream()

    rows = []

    for doc in docs:
        p = doc.to_dict()
        rows.append((
            p.get("product_name"),
            float(p.get("price", 0)),
            p.get("item"),
            p.get("created_at")
        ))

    rows.sort(key=lambda x: x[3] or "", reverse=True)
    return rows[:10]


def stats():
    users_docs = list(db.collection("users").stream())
    purchases_docs = list(db.collection("purchases").stream())

    total_users = len(users_docs)
    total_balance = 0.0

    for doc in users_docs:
        total_balance += float(doc.to_dict().get("balance", 0))

    total_purchases = len(purchases_docs)

    return total_users, total_balance, total_purchases