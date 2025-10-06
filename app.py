"""
Open http://127.0.0.1:8080/
"""
from flask import Flask, request, redirect, url_for, render_template_string, flash
from flask_sqlalchemy import SQLAlchemy
import uuid
from datetime import datetime
import random

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'dev-key'

db = SQLAlchemy(app)

# Models
class Product(db.Model):
    product_id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.String)

    def __repr__(self):
        return f"<Product {self.name}>"

class Location(db.Model):
    location_id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.String)

    def __repr__(self):
        return f"<Location {self.name}>"

class ProductMovement(db.Model):
    movement_id = db.Column(db.String, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    from_location = db.Column(db.String, db.ForeignKey('location.location_id'), nullable=True)
    to_location = db.Column(db.String, db.ForeignKey('location.location_id'), nullable=True)
    product_id = db.Column(db.String, db.ForeignKey('product.product_id'), nullable=False)
    qty = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"<Move {self.product_id} {self.qty} from {self.from_location} to {self.to_location}>"

# DB init helper
@app.before_request
def create_tables_once():
    if not hasattr(app, 'tables_created'):
        db.create_all()
        app.tables_created = True

# Templates (kept compact)
base_tpl = '''
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Inventory App</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  </head>
  <body class="p-4">
    <div class="container">
      <h1 class="mb-4">Inventory Manager</h1>
      <nav class="mb-3">
        <a class="btn btn-sm btn-outline-primary" href="{{ url_for('products') }}">Products</a>
        <a class="btn btn-sm btn-outline-primary" href="{{ url_for('locations') }}">Locations</a>
        <a class="btn btn-sm btn-outline-primary" href="{{ url_for('movements') }}">Movements</a>
        <a class="btn btn-sm btn-outline-success" href="{{ url_for('report') }}">Balance Report</a>
        <a class="btn btn-sm btn-outline-secondary" href="{{ url_for('seed') }}">Seed sample data</a>
      </nav>
      {% with messages = get_flashed_messages() %}
        {% if messages %}
          {% for m in messages %}
            <div class="alert alert-info">{{ m }}</div>
          {% endfor %}
        {% endif %}
      {% endwith %}
      {{ body|safe }}
    </div>
  </body>
</html>
'''

# Products
@app.route('/products')
def products():
    prods = Product.query.order_by(Product.name).all()
    body = '''
    <div class="d-flex justify-content-between align-items-center mb-2">
      <h2>Products</h2>
      <a class="btn btn-primary" href="{{ url_for('add_product') }}">Add Product</a>
    </div>
    <table class="table table-sm">
      <thead><tr><th>ID</th><th>Name</th><th>Description</th><th>Actions</th></tr></thead>
      <tbody>
      {% for p in prods %}
        <tr>
          <td>{{ p.product_id }}</td>
          <td>{{ p.name }}</td>
          <td>{{ p.description or '' }}</td>
          <td>
            <a class="btn btn-sm btn-outline-secondary" href="{{ url_for('edit_product', id=p.product_id) }}">Edit</a>
          </td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
    '''
    return render_template_string(base_tpl, body=body, prods=prods)

@app.route('/products/add', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        pid = request.form.get('product_id') or str(uuid.uuid4())
        name = request.form['name']
        desc = request.form.get('description')
        if not name:
            flash('Name required')
        else:
            db.session.add(Product(product_id=pid, name=name, description=desc))
            db.session.commit()
            flash('Product added')
            return redirect(url_for('products'))
    body = '''
    <h2>Add Product</h2>
    <form method="post">
      <div class="mb-3">
        <label class="form-label">ID (optional)</label>
        <input class="form-control" name="product_id">
      </div>
      <div class="mb-3">
        <label class="form-label">Name</label>
        <input class="form-control" name="name" required>
      </div>
      <div class="mb-3">
        <label class="form-label">Description</label>
        <textarea class="form-control" name="description"></textarea>
      </div>
      <button class="btn btn-primary">Save</button>
    </form>
    '''
    return render_template_string(base_tpl, body=body)

@app.route('/products/edit/<id>', methods=['GET', 'POST'])
def edit_product(id):
    p = Product.query.get_or_404(id)
    if request.method == 'POST':
        p.name = request.form['name']
        p.description = request.form.get('description')
        db.session.commit()
        flash('Product updated')
        return redirect(url_for('products'))
    body = '''
    <h2>Edit Product</h2>
    <form method="post">
      <div class="mb-3">
        <label class="form-label">ID</label>
        <input class="form-control" name="product_id" value="{{ p.product_id }}" readonly>
      </div>
      <div class="mb-3">
        <label class="form-label">Name</label>
        <input class="form-control" name="name" value="{{ p.name }}" required>
      </div>
      <div class="mb-3">
        <label class="form-label">Description</label>
        <textarea class="form-control" name="description">{{ p.description or '' }}</textarea>
      </div>
      <button class="btn btn-primary">Save</button>
    </form>
    '''
    return render_template_string(base_tpl, body=body, p=p)

# Locations
@app.route('/locations')
def locations():
    locs = Location.query.order_by(Location.name).all()
    body = '''
    <div class="d-flex justify-content-between align-items-center mb-2">
      <h2>Locations</h2>
      <a class="btn btn-primary" href="{{ url_for('add_location') }}">Add Location</a>
    </div>
    <table class="table table-sm">
      <thead><tr><th>ID</th><th>Name</th><th>Description</th><th>Actions</th></tr></thead>
      <tbody>
      {% for l in locs %}
        <tr>
          <td>{{ l.location_id }}</td>
          <td>{{ l.name }}</td>
          <td>{{ l.description or '' }}</td>
          <td>
            <a class="btn btn-sm btn-outline-secondary" href="{{ url_for('edit_location', id=l.location_id) }}">Edit</a>
          </td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
    '''
    return render_template_string(base_tpl, body=body, locs=locs)

@app.route('/locations/add', methods=['GET', 'POST'])
def add_location():
    if request.method == 'POST':
        lid = request.form.get('location_id') or str(uuid.uuid4())
        name = request.form['name']
        desc = request.form.get('description')
        if not name:
            flash('Name required')
        else:
            db.session.add(Location(location_id=lid, name=name, description=desc))
            db.session.commit()
            flash('Location added')
            return redirect(url_for('locations'))
    body = '''
    <h2>Add Location</h2>
    <form method="post">
      <div class="mb-3">
        <label class="form-label">ID (optional)</label>
        <input class="form-control" name="location_id">
      </div>
      <div class="mb-3">
        <label class="form-label">Name</label>
        <input class="form-control" name="name" required>
      </div>
      <div class="mb-3">
        <label class="form-label">Description</label>
        <textarea class="form-control" name="description"></textarea>
      </div>
      <button class="btn btn-primary">Save</button>
    </form>
    '''
    return render_template_string(base_tpl, body=body)

@app.route('/locations/edit/<id>', methods=['GET', 'POST'])
def edit_location(id):
    l = Location.query.get_or_404(id)
    if request.method == 'POST':
        l.name = request.form['name']
        l.description = request.form.get('description')
        db.session.commit()
        flash('Location updated')
        return redirect(url_for('locations'))
    body = '''
    <h2>Edit Location</h2>
    <form method="post">
      <div class="mb-3">
        <label class="form-label">ID</label>
        <input class="form-control" name="location_id" value="{{ l.location_id }}" readonly>
      </div>
      <div class="mb-3">
        <label class="form-label">Name</label>
        <input class="form-control" name="name" value="{{ l.name }}" required>
      </div>
      <div class="mb-3">
        <label class="form-label">Description</label>
        <textarea class="form-control" name="description">{{ l.description or '' }}</textarea>
      </div>
      <button class="btn btn-primary">Save</button>
    </form>
    '''
    return render_template_string(base_tpl, body=body, l=l)

# Movements
@app.route('/movements')
def movements():
    moves = ProductMovement.query.order_by(ProductMovement.timestamp.desc()).limit(200).all()
    prods = Product.query.order_by(Product.name).all()
    locs = Location.query.order_by(Location.name).all()
    body = '''
    <div class="d-flex justify-content-between align-items-center mb-2">
      <h2>Product Movements</h2>
      <a class="btn btn-primary" href="{{ url_for('add_movement') }}">Add Movement</a>
    </div>
    <table class="table table-sm">
      <thead><tr><th>When</th><th>Product</th><th>From</th><th>To</th><th>Qty</th><th>ID</th></tr></thead>
      <tbody>
      {% for m in moves %}
        <tr>
          <td>{{ m.timestamp }}</td>
          <td>{{ m.product_id }}</td>
          <td>{{ m.from_location or '' }}</td>
          <td>{{ m.to_location or '' }}</td>
          <td>{{ m.qty }}</td>
          <td>{{ m.movement_id }}</td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
    '''
    return render_template_string(base_tpl, body=body, moves=moves, prods=prods, locs=locs)

@app.route('/movements/add', methods=['GET', 'POST'])
def add_movement():
    prods = Product.query.order_by(Product.name).all()
    locs = Location.query.order_by(Location.name).all()
    if request.method == 'POST':
        pid = request.form['product_id']
        from_loc = request.form.get('from_location') or None
        to_loc = request.form.get('to_location') or None
        qty = int(request.form['qty'])
        if not pid or qty <= 0:
            flash('Product and positive qty required')
        else:
            mid = str(uuid.uuid4())
            move = ProductMovement(movement_id=mid, product_id=pid, from_location=from_loc, to_location=to_loc, qty=qty)
            db.session.add(move)
            db.session.commit()
            flash('Movement recorded')
            return redirect(url_for('movements'))
    body = '''
    <h2>Add Movement</h2>
    <form method="post">
      <div class="mb-3">
        <label class="form-label">Product</label>
        <select class="form-select" name="product_id">
          {% for p in prods %}
            <option value="{{ p.product_id }}">{{ p.name }} ({{ p.product_id }})</option>
          {% endfor %}
        </select>
      </div>
      <div class="mb-3">
        <label class="form-label">From (optional)</label>
        <select class="form-select" name="from_location">
          <option value="">-- none --</option>
          {% for l in locs %}
            <option value="{{ l.location_id }}">{{ l.name }} ({{ l.location_id }})</option>
          {% endfor %}
        </select>
      </div>
      <div class="mb-3">
        <label class="form-label">To (optional)</label>
        <select class="form-select" name="to_location">
          <option value="">-- none --</option>
          {% for l in locs %}
            <option value="{{ l.location_id }}">{{ l.name }} ({{ l.location_id }})</option>
          {% endfor %}
        </select>
      </div>
      <div class="mb-3">
        <label class="form-label">Qty</label>
        <input class="form-control" name="qty" type="number" value="1" min="1">
      </div>
      <button class="btn btn-primary">Save</button>
    </form>
    '''
    return render_template_string(base_tpl, body=body, prods=prods, locs=locs)

# Report: balance per product per location
@app.route('/report')
def report():
    products = Product.query.order_by(Product.name).all()
    locations = Location.query.order_by(Location.name).all()

    # Build balances dict: balances[product_id][location_id] = qty
    balances = {p.product_id: {l.location_id: 0 for l in locations} for p in products}

    moves = ProductMovement.query.all()
    for m in moves:
        if m.to_location:
            balances.setdefault(m.product_id, {})
            balances[m.product_id].setdefault(m.to_location, 0)
            balances[m.product_id][m.to_location] += m.qty
        if m.from_location:
            balances.setdefault(m.product_id, {})
            balances[m.product_id].setdefault(m.from_location, 0)
            balances[m.product_id][m.from_location] -= m.qty

    # Prepare rows for display (only non-zero entries)
    rows = []
    for p in products:
        for l in locations:
            qty = balances.get(p.product_id, {}).get(l.location_id, 0)
            if qty != 0:
                rows.append({'product': p.name, 'warehouse': l.name, 'qty': qty})

    body = '''
    <h2>Balance Report</h2>
    <p>Grid shows Product | Warehouse | Qty (non-zero balances)</p>
    <table class="table table-sm">
      <thead><tr><th>Product</th><th>Warehouse</th><th>Qty</th></tr></thead>
      <tbody>
      {% for r in rows %}
        <tr>
          <td>{{ r.product }}</td>
          <td>{{ r.warehouse }}</td>
          <td>{{ r.qty }}</td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
    {% if not rows %}
      <div class="alert alert-warning">No stock movements yet (balances all zero).</div>
    {% endif %}
    '''
    return render_template_string(base_tpl, body=body, rows=rows)

# Seed route to create sample data and random movements
@app.route('/seed')
def seed():
    # Create sample products and locations if they don't exist
    sample_products = [
        ('P-A', 'Product A'),
        ('P-B', 'Product B'),
        ('P-C', 'Product C'),
        ('P-D', 'Product D'),
    ]
    sample_locations = [
        ('L-X', 'Location X'),
        ('L-Y', 'Location Y'),
        ('L-Z', 'Location Z'),
    ]
    for pid, name in sample_products:
        if not Product.query.get(pid):
            db.session.add(Product(product_id=pid, name=name))
    for lid, name in sample_locations:
        if not Location.query.get(lid):
            db.session.add(Location(location_id=lid, name=name))
    db.session.commit()

    prods = [p.product_id for p in Product.query.all()]
    locs = [l.location_id for l in Location.query.all()]

    # Create 20 movements
    for i in range(20):
        pid = random.choice(prods)
        # randomly decide move in, out, or between
        t = random.choice(['in', 'out', 'transfer'])
        qty = random.randint(1, 10)
        if t == 'in':
            from_loc = None
            to_loc = random.choice(locs)
        elif t == 'out':
            from_loc = random.choice(locs)
            to_loc = None
        else:
            from_loc = random.choice(locs)
            to_loc = random.choice(locs)
            # avoid same place transfer
            if from_loc == to_loc:
                to_loc = None
        move = ProductMovement(movement_id=str(uuid.uuid4()), product_id=pid, from_location=from_loc, to_location=to_loc, qty=qty)
        db.session.add(move)
    db.session.commit()
    flash('Seeded sample products, locations and 20 movements')
    return redirect(url_for('products'))

@app.route('/')
def index():
    return redirect(url_for('report'))

if __name__ == '__main__':
    app.run(debug=True, port=8080)