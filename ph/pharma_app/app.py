from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from datetime import datetime
from functools import wraps
import hashlib

app = Flask(__name__)
app.secret_key = 'sterling_labs_secret_2024'
DB_PATH = 'database.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL,
        product_type TEXT NOT NULL,
        unit TEXT NOT NULL,
        reorder_level INTEGER DEFAULT 50,
        current_stock INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS batches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        batch_number TEXT NOT NULL UNIQUE,
        product_id INTEGER NOT NULL,
        manufacture_date TEXT NOT NULL,
        expiry_date TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        qc_status TEXT DEFAULT 'Pending',
        ph_level TEXT, purity TEXT, moisture TEXT, remarks TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES products(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS stock_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        change_type TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        date TEXT NOT NULL,
        reference TEXT,
        FOREIGN KEY (product_id) REFERENCES products(id)
    )''')

    # Default user
    c.execute('SELECT COUNT(*) FROM users')
    if c.fetchone()[0] == 0:
        c.execute('INSERT INTO users (username,password) VALUES (?,?)',
                  ('admin', hash_password('admin123')))

    # Products
    sample_products = [
        ('Amoxicillin 500mg','Medicine','Units',100,0),
        ('Paracetamol 650mg','Medicine','Units',150,0),
        ('Ibuprofen 400mg','Medicine','Units',100,0),
        ('Vitamin C 1000mg','Nutraceutical','Units',80,0),
        ('Ethanol 99%','Lab Chemical','Litres',20,0),
        ('Sodium Chloride API','API','kg',30,0),
        ('HCl Reagent','Lab Chemical','Litres',15,0),
        ('Glucose Powder','API','kg',40,0),
        ('Blister Pack 10s','Packaging','Packs',500,0),
        ('Veterinary Ivermectin','Veterinary','Units',60,0),
    ]
    c.execute('SELECT COUNT(*) FROM products')
    if c.fetchone()[0] == 0:
        c.executemany('INSERT INTO products (product_name,product_type,unit,reorder_level,current_stock) VALUES (?,?,?,?,?)', sample_products)

    # Batches (March + April 2024 — two full months)
    sample_batches = [
        # March 2024
        ('SL-MAR-001',1,'2024-03-02','2026-03-02',500,'Pass','6.8','99.2','0.3','March batch - Amoxicillin'),
        ('SL-MAR-002',2,'2024-03-04','2026-03-04',600,'Pass','7.0','98.8','0.4','March batch - Paracetamol'),
        ('SL-MAR-003',3,'2024-03-06','2026-03-06',400,'Pass','6.9','99.0','0.3','March batch - Ibuprofen'),
        ('SL-MAR-004',4,'2024-03-08','2025-12-08',300,'Pass','7.0','99.5','0.2','March batch - Vit C'),
        ('SL-MAR-005',5,'2024-03-10','2025-09-10',80,'Pass','—','99.1','0.4','Ethanol cleared'),
        ('SL-MAR-006',6,'2024-03-12','2026-03-12',200,'Pass','7.1','98.0','0.5','NaCl API batch'),
        ('SL-MAR-007',7,'2024-03-14','2025-09-14',60,'Fail','4.0','88.0','2.0','Purity too low - rejected'),
        ('SL-MAR-008',8,'2024-03-16','2026-03-16',250,'Pass','7.0','99.8','0.1','Glucose batch'),
        ('SL-MAR-009',9,'2024-03-18','2026-03-18',1000,'Pass','—','—','—','Packaging cleared'),
        ('SL-MAR-010',10,'2024-03-20','2026-03-20',180,'Pass','6.7','98.5','0.3','Vet Ivermectin'),
        ('SL-MAR-011',1,'2024-03-22','2026-03-22',300,'Pending','','','','In QC testing'),
        ('SL-MAR-012',2,'2024-03-25','2026-03-25',200,'Fail','5.2','91.0','1.2','pH out of range'),
        # April 2024
        ('SL-APR-001',1,'2024-04-01','2026-04-01',550,'Pass','6.9','99.4','0.2','April batch - Amoxicillin'),
        ('SL-APR-002',2,'2024-04-03','2026-04-03',700,'Pass','7.0','99.0','0.3','April batch - Paracetamol'),
        ('SL-APR-003',3,'2024-04-05','2026-04-05',350,'Pass','6.8','98.5','0.4','April batch - Ibuprofen'),
        ('SL-APR-004',4,'2024-04-07','2025-11-07',400,'Pass','7.1','99.6','0.2','April batch - Vit C'),
        ('SL-APR-005',5,'2024-04-09','2025-10-09',90,'Pass','—','99.3','0.3','Ethanol April'),
        ('SL-APR-006',6,'2024-04-11','2026-04-11',220,'Pass','7.0','98.2','0.5','NaCl API April'),
        ('SL-APR-007',7,'2024-04-13','2025-10-13',70,'Pass','6.9','99.0','0.4','HCl cleared this time'),
        ('SL-APR-008',8,'2024-04-15','2026-04-15',280,'Pass','7.0','99.9','0.1','Glucose April'),
        ('SL-APR-009',9,'2024-04-17','2026-04-17',1200,'Pass','—','—','—','Packaging April'),
        ('SL-APR-010',10,'2024-04-19','2026-04-19',200,'Pass','6.8','98.8','0.3','Vet April'),
        ('SL-APR-011',1,'2024-04-22','2026-04-22',400,'Pending','','','','Awaiting QC'),
        ('SL-APR-012',3,'2024-04-25','2026-04-25',180,'Fail','5.0','90.0','1.5','Failed - moisture high'),
    ]

    c.execute('SELECT COUNT(*) FROM batches')
    if c.fetchone()[0] == 0:
        c.executemany('''INSERT INTO batches (batch_number,product_id,manufacture_date,expiry_date,quantity,qc_status,ph_level,purity,moisture,remarks)
            VALUES (?,?,?,?,?,?,?,?,?,?)''', sample_batches)

        # Stock IN for all Pass batches
        passed_batches = [
            (1,500,'2024-03-02','SL-MAR-001'),(2,600,'2024-03-04','SL-MAR-002'),
            (3,400,'2024-03-06','SL-MAR-003'),(4,300,'2024-03-08','SL-MAR-004'),
            (5,80,'2024-03-10','SL-MAR-005'),(6,200,'2024-03-12','SL-MAR-006'),
            (8,250,'2024-03-16','SL-MAR-008'),(9,1000,'2024-03-18','SL-MAR-009'),
            (10,180,'2024-03-20','SL-MAR-010'),
            (1,550,'2024-04-01','SL-APR-001'),(2,700,'2024-04-03','SL-APR-002'),
            (3,350,'2024-04-05','SL-APR-003'),(4,400,'2024-04-07','SL-APR-004'),
            (5,90,'2024-04-09','SL-APR-005'),(6,220,'2024-04-11','SL-APR-006'),
            (7,70,'2024-04-13','SL-APR-007'),(8,280,'2024-04-15','SL-APR-008'),
            (9,1200,'2024-04-17','SL-APR-009'),(10,200,'2024-04-19','SL-APR-010'),
        ]
        for pid,qty,date,ref in passed_batches:
            c.execute('UPDATE products SET current_stock=current_stock+? WHERE id=?',(qty,pid))
            c.execute('INSERT INTO stock_log (product_id,change_type,quantity,date,reference) VALUES (?,?,?,?,?)',(pid,'IN',qty,date,ref))

        # ── MARCH Stock OUT (dispatch/sales) ──
        march_out = [
            (1,120,'2024-03-05','ORD-MAR-101'),(2,200,'2024-03-06','ORD-MAR-102'),
            (3,90,'2024-03-07','ORD-MAR-103'),(4,80,'2024-03-09','ORD-MAR-104'),
            (1,150,'2024-03-12','ORD-MAR-105'),(2,180,'2024-03-13','ORD-MAR-106'),
            (3,100,'2024-03-14','ORD-MAR-107'),(8,60,'2024-03-15','ORD-MAR-108'),
            (10,50,'2024-03-16','ORD-MAR-109'),(4,70,'2024-03-18','ORD-MAR-110'),
            (6,40,'2024-03-19','ORD-MAR-111'),(5,20,'2024-03-20','ORD-MAR-112'),
            (1,80,'2024-03-22','ORD-MAR-113'),(2,120,'2024-03-24','ORD-MAR-114'),
            (9,150,'2024-03-26','ORD-MAR-115'),(3,60,'2024-03-28','ORD-MAR-116'),
            (10,40,'2024-03-29','ORD-MAR-117'),(4,50,'2024-03-30','ORD-MAR-118'),
        ]
        # ── APRIL Stock OUT (dispatch/sales) ──
        april_out = [
            (1,180,'2024-04-02','ORD-APR-101'),(2,250,'2024-04-03','ORD-APR-102'),
            (3,130,'2024-04-04','ORD-APR-103'),(4,110,'2024-04-05','ORD-APR-104'),
            (1,200,'2024-04-08','ORD-APR-105'),(2,220,'2024-04-09','ORD-APR-106'),
            (3,90,'2024-04-10','ORD-APR-107'),(8,100,'2024-04-11','ORD-APR-108'),
            (10,80,'2024-04-12','ORD-APR-109'),(4,90,'2024-04-14','ORD-APR-110'),
            (6,60,'2024-04-15','ORD-APR-111'),(5,30,'2024-04-16','ORD-APR-112'),
            (7,40,'2024-04-17','ORD-APR-113'),(1,150,'2024-04-18','ORD-APR-114'),
            (2,180,'2024-04-20','ORD-APR-115'),(9,200,'2024-04-22','ORD-APR-116'),
            (3,100,'2024-04-24','ORD-APR-117'),(10,70,'2024-04-26','ORD-APR-118'),
            (4,80,'2024-04-28','ORD-APR-119'),(1,120,'2024-04-30','ORD-APR-120'),
        ]
        for pid,qty,date,ref in march_out + april_out:
            c.execute('UPDATE products SET current_stock=MAX(0,current_stock-?) WHERE id=?',(qty,pid))
            c.execute('INSERT INTO stock_log (product_id,change_type,quantity,date,reference) VALUES (?,?,?,?,?)',(pid,'OUT',qty,date,ref))

    conn.commit()
    conn.close()

# ── AUTH ──────────────────────────────────────────
@app.route('/login', methods=['GET','POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username=? AND password=?',
                            (username, hash_password(password))).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash(f'Welcome back, {user["username"]}!', 'success')
            return redirect(url_for('index'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/settings', methods=['GET','POST'])
@login_required
def settings():
    if request.method == 'POST':
        new_username     = request.form['new_username'].strip()
        current_password = request.form['current_password']
        new_password     = request.form['new_password']
        confirm_password = request.form['confirm_password']
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE id=? AND password=?',
                            (session['user_id'], hash_password(current_password))).fetchone()
        if not user:
            flash('Current password is incorrect.', 'danger')
        elif new_password != confirm_password:
            flash('New passwords do not match.', 'danger')
        elif len(new_password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
        else:
            conn.execute('UPDATE users SET username=?, password=? WHERE id=?',
                         (new_username, hash_password(new_password), session['user_id']))
            conn.commit()
            session['username'] = new_username
            flash('Credentials updated successfully!', 'success')
        conn.close()
        return redirect(url_for('settings'))
    return render_template('settings.html')

# ── DASHBOARD ─────────────────────────────────────
@app.route('/')
@login_required
def index():
    conn = get_db()
    total_products = conn.execute('SELECT COUNT(*) FROM products').fetchone()[0]
    total_batches  = conn.execute('SELECT COUNT(*) FROM batches').fetchone()[0]
    passed  = conn.execute("SELECT COUNT(*) FROM batches WHERE qc_status='Pass'").fetchone()[0]
    failed  = conn.execute("SELECT COUNT(*) FROM batches WHERE qc_status='Fail'").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM batches WHERE qc_status='Pending'").fetchone()[0]
    low_stock      = conn.execute('SELECT * FROM products WHERE current_stock < reorder_level').fetchall()
    recent_batches = conn.execute('''SELECT b.*,p.product_name FROM batches b
        JOIN products p ON b.product_id=p.id ORDER BY b.id DESC LIMIT 5''').fetchall()
    conn.close()
    return render_template('index.html', total_products=total_products, total_batches=total_batches,
                           passed=passed, failed=failed, pending=pending,
                           low_stock=low_stock, recent_batches=recent_batches)

# ── INVENTORY ─────────────────────────────────────
@app.route('/inventory')
@login_required
def inventory():
    sort   = request.args.get('sort','name_asc')
    status = request.args.get('status','all')
    order_map = {'name_asc':'product_name ASC','name_desc':'product_name DESC',
                 'stock_asc':'current_stock ASC','stock_desc':'current_stock DESC'}
    order_sql = order_map.get(sort,'product_name ASC')
    where_sql = ''
    if status == 'low':  where_sql = 'WHERE current_stock < reorder_level'
    elif status == 'ok': where_sql = 'WHERE current_stock >= reorder_level'
    conn = get_db()
    products = conn.execute(f'SELECT * FROM products {where_sql} ORDER BY {order_sql}').fetchall()
    conn.close()
    return render_template('inventory.html', products=products, sort=sort, status=status)

@app.route('/inventory/add', methods=['GET','POST'])
@login_required
def add_product():
    if request.method == 'POST':
        conn = get_db()
        conn.execute('INSERT INTO products (product_name,product_type,unit,reorder_level,current_stock) VALUES (?,?,?,?,0)',
                     (request.form['product_name'],request.form['product_type'],request.form['unit'],request.form['reorder_level']))
        conn.commit(); conn.close()
        flash('Product added!','success')
        return redirect(url_for('inventory'))
    return render_template('add_product.html')

@app.route('/inventory/edit/<int:pid>', methods=['GET','POST'])
@login_required
def edit_product(pid):
    conn = get_db()
    if request.method == 'POST':
        conn.execute('UPDATE products SET product_name=?,product_type=?,unit=?,reorder_level=? WHERE id=?',
                     (request.form['product_name'],request.form['product_type'],request.form['unit'],request.form['reorder_level'],pid))
        conn.commit(); conn.close()
        flash('Product updated!','success')
        return redirect(url_for('inventory'))
    product = conn.execute('SELECT * FROM products WHERE id=?',(pid,)).fetchone()
    conn.close()
    return render_template('edit_product.html', product=product)

@app.route('/inventory/delete/<int:pid>')
@login_required
def delete_product(pid):
    conn = get_db()
    conn.execute('DELETE FROM products WHERE id=?',(pid,))
    conn.commit(); conn.close()
    flash('Product deleted.','danger')
    return redirect(url_for('inventory'))

@app.route('/inventory/stock_out/<int:pid>', methods=['POST'])
@login_required
def stock_out(pid):
    qty = int(request.form['quantity'])
    conn = get_db()
    product = conn.execute('SELECT * FROM products WHERE id=?',(pid,)).fetchone()
    if product['current_stock'] >= qty:
        conn.execute('UPDATE products SET current_stock=current_stock-? WHERE id=?',(qty,pid))
        conn.execute('INSERT INTO stock_log (product_id,change_type,quantity,date,reference) VALUES (?,?,?,?,?)',
                     (pid,'OUT',qty,datetime.now().strftime('%Y-%m-%d'),'Manual dispatch'))
        conn.commit()
        flash(f'Stock out: {qty} units recorded.','success')
    else:
        flash('Insufficient stock!','danger')
    conn.close()
    return redirect(url_for('inventory'))

# ── BATCHES ───────────────────────────────────────
@app.route('/batches')
@login_required
def batches():
    sort   = request.args.get('sort','date_desc')
    status = request.args.get('status','all')
    order_map = {'name_asc':'p.product_name ASC','name_desc':'p.product_name DESC',
                 'date_asc':'b.manufacture_date ASC','date_desc':'b.manufacture_date DESC',
                 'batch_asc':'b.batch_number ASC','batch_desc':'b.batch_number DESC'}
    order_sql = order_map.get(sort,'b.manufacture_date DESC')
    where_sql = ''
    if status in ('Pass','Fail','Pending'):
        where_sql = f"WHERE b.qc_status='{status}'"
    conn = get_db()
    all_batches = conn.execute(f'''SELECT b.*,p.product_name,p.unit FROM batches b
        JOIN products p ON b.product_id=p.id {where_sql} ORDER BY {order_sql}''').fetchall()
    conn.close()
    return render_template('batches.html', batches=all_batches, sort=sort, status=status)

@app.route('/batches/add', methods=['GET','POST'])
@login_required
def add_batch():
    conn = get_db()
    if request.method == 'POST':
        batch_num=request.form['batch_number']; product_id=request.form['product_id']
        mfg_date=request.form['manufacture_date']; exp_date=request.form['expiry_date']
        qty=int(request.form['quantity']); qc_status=request.form['qc_status']
        ph=request.form.get('ph_level',''); purity=request.form.get('purity','')
        moisture=request.form.get('moisture',''); remarks=request.form.get('remarks','')
        conn.execute('''INSERT INTO batches (batch_number,product_id,manufacture_date,expiry_date,quantity,qc_status,ph_level,purity,moisture,remarks)
            VALUES (?,?,?,?,?,?,?,?,?,?)''',(batch_num,product_id,mfg_date,exp_date,qty,qc_status,ph,purity,moisture,remarks))
        if qc_status == 'Pass':
            conn.execute('UPDATE products SET current_stock=current_stock+? WHERE id=?',(qty,product_id))
            conn.execute('INSERT INTO stock_log (product_id,change_type,quantity,date,reference) VALUES (?,?,?,?,?)',
                         (product_id,'IN',qty,mfg_date,batch_num))
        conn.commit(); conn.close()
        flash('Batch logged!','success')
        return redirect(url_for('batches'))
    products = conn.execute('SELECT * FROM products ORDER BY product_name').fetchall()
    conn.close()
    return render_template('add_batch.html', products=products)

@app.route('/batches/update_qc/<int:bid>', methods=['POST'])
@login_required
def update_qc(bid):
    new_status = request.form['qc_status']
    conn = get_db()
    batch = conn.execute('SELECT * FROM batches WHERE id=?',(bid,)).fetchone()
    old_status = batch['qc_status']
    conn.execute('UPDATE batches SET qc_status=? WHERE id=?',(new_status,bid))
    if old_status != 'Pass' and new_status == 'Pass':
        conn.execute('UPDATE products SET current_stock=current_stock+? WHERE id=?',(batch['quantity'],batch['product_id']))
        conn.execute('INSERT INTO stock_log (product_id,change_type,quantity,date,reference) VALUES (?,?,?,?,?)',
                     (batch['product_id'],'IN',batch['quantity'],datetime.now().strftime('%Y-%m-%d'),batch['batch_number']))
    elif old_status == 'Pass' and new_status != 'Pass':
        conn.execute('UPDATE products SET current_stock=MAX(0,current_stock-?) WHERE id=?',(batch['quantity'],batch['product_id']))
    conn.commit(); conn.close()
    flash(f'QC updated to {new_status}!','success')
    return redirect(url_for('batches'))

# ── STOCK LOG ─────────────────────────────────────
@app.route('/stock_log')
@login_required
def stock_log():
    sort        = request.args.get('sort','date_desc')
    filter_type = request.args.get('type','all')
    order_map = {'name_asc':'p.product_name ASC','name_desc':'p.product_name DESC',
                 'date_asc':'sl.date ASC','date_desc':'sl.date DESC'}
    order_sql = order_map.get(sort,'sl.date DESC')
    where_sql = ''
    if filter_type in ('IN','OUT'):
        where_sql = f"WHERE sl.change_type='{filter_type}'"
    conn = get_db()
    logs = conn.execute(f'''SELECT sl.*,p.product_name,p.unit FROM stock_log sl
        JOIN products p ON sl.product_id=p.id {where_sql} ORDER BY {order_sql}''').fetchall()
    conn.close()
    return render_template('stock_log.html', logs=logs, sort=sort, filter_type=filter_type)

# ── ANALYTICS ─────────────────────────────────────
@app.route('/analytics')
@login_required
def analytics():
    conn = get_db()
    products    = conn.execute('SELECT product_name,current_stock,reorder_level,product_type FROM products').fetchall()
    batch_stats = conn.execute('SELECT qc_status,COUNT(*) as count FROM batches GROUP BY qc_status').fetchall()
    type_stats  = conn.execute('SELECT product_type,COUNT(*) as count FROM products GROUP BY product_type').fetchall()
    low_stock   = conn.execute('SELECT product_name,current_stock FROM products WHERE current_stock < reorder_level').fetchall()
    conn.close()
    return render_template('analytics.html', products=products, batch_stats=batch_stats,
                           type_stats=type_stats, low_stock=low_stock)

# ── MONTHLY COMPARISON ────────────────────────────
@app.route('/comparison')
@login_required
def comparison():
    conn = get_db()

    # Total dispatched per month
    mar_total = conn.execute(
        "SELECT COALESCE(SUM(quantity),0) FROM stock_log WHERE change_type='OUT' AND date LIKE '2024-03-%'"
    ).fetchone()[0]
    apr_total = conn.execute(
        "SELECT COALESCE(SUM(quantity),0) FROM stock_log WHERE change_type='OUT' AND date LIKE '2024-04-%'"
    ).fetchone()[0]

    # Per-product breakdown both months
    mar_by_product = conn.execute('''
        SELECT p.product_name, p.product_type, COALESCE(SUM(sl.quantity),0) as total
        FROM products p
        LEFT JOIN stock_log sl ON sl.product_id=p.id AND sl.change_type='OUT' AND sl.date LIKE '2024-03-%'
        GROUP BY p.id ORDER BY total DESC
    ''').fetchall()
    apr_by_product = conn.execute('''
        SELECT p.product_name, p.product_type, COALESCE(SUM(sl.quantity),0) as total
        FROM products p
        LEFT JOIN stock_log sl ON sl.product_id=p.id AND sl.change_type='OUT' AND sl.date LIKE '2024-04-%'
        GROUP BY p.id ORDER BY total DESC
    ''').fetchall()

    # Batches produced per month
    mar_batches = conn.execute("SELECT COUNT(*) FROM batches WHERE manufacture_date LIKE '2024-03-%'").fetchone()[0]
    apr_batches = conn.execute("SELECT COUNT(*) FROM batches WHERE manufacture_date LIKE '2024-04-%'").fetchone()[0]

    # QC pass rate per month
    mar_pass = conn.execute("SELECT COUNT(*) FROM batches WHERE manufacture_date LIKE '2024-03-%' AND qc_status='Pass'").fetchone()[0]
    apr_pass = conn.execute("SELECT COUNT(*) FROM batches WHERE manufacture_date LIKE '2024-04-%' AND qc_status='Pass'").fetchone()[0]

    # Stock IN per month
    mar_in = conn.execute("SELECT COALESCE(SUM(quantity),0) FROM stock_log WHERE change_type='IN' AND date LIKE '2024-03-%'").fetchone()[0]
    apr_in = conn.execute("SELECT COALESCE(SUM(quantity),0) FROM stock_log WHERE change_type='IN' AND date LIKE '2024-04-%'").fetchone()[0]

    # Day-wise OUT for sparkline (march)
    mar_daily = conn.execute('''
        SELECT date, SUM(quantity) as qty FROM stock_log
        WHERE change_type='OUT' AND date LIKE '2024-03-%' GROUP BY date ORDER BY date
    ''').fetchall()
    apr_daily = conn.execute('''
        SELECT date, SUM(quantity) as qty FROM stock_log
        WHERE change_type='OUT' AND date LIKE '2024-04-%' GROUP BY date ORDER BY date
    ''').fetchall()

    conn.close()

    winner = 'April 2024' if apr_total > mar_total else 'March 2024' if mar_total > apr_total else 'Tie'
    diff   = abs(apr_total - mar_total)
    pct    = round((diff / mar_total * 100), 1) if mar_total > 0 else 0

    return render_template('comparison.html',
        mar_total=mar_total, apr_total=apr_total,
        mar_by_product=mar_by_product, apr_by_product=apr_by_product,
        mar_batches=mar_batches, apr_batches=apr_batches,
        mar_pass=mar_pass, apr_pass=apr_pass,
        mar_in=mar_in, apr_in=apr_in,
        mar_daily=mar_daily, apr_daily=apr_daily,
        winner=winner, diff=diff, pct=pct
    )

@app.context_processor
def inject_globals():
    return {'now': datetime.now().strftime('%d %b %Y'), 'current_user': session.get('username','')}

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
