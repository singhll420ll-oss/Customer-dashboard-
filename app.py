from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from dotenv import load_dotenv
import json

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'bitebuddy-secret-key-2024')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'index'

# ===================== DATABASE TABLES =====================

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    mobile = db.Column(db.String(15), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True)
    location = db.Column(db.String(200))
    password = db.Column(db.String(200), nullable=False)
    profile_pic = db.Column(db.String(500), default='')
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)

class Service(db.Model):
    __tablename__ = 'services'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))
    base_price = db.Column(db.Float, nullable=False)
    discount = db.Column(db.Float, default=0)
    final_price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(500))
    description = db.Column(db.Text)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    available = db.Column(db.Boolean, default=True)

class ServiceItem(db.Model):
    __tablename__ = 'service_items'
    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    image_url = db.Column(db.String(500))
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    service = db.relationship('Service', backref='items')

class Menu(db.Model):
    __tablename__ = 'menu'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    image_url = db.Column(db.String(500))
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    discount = db.Column(db.Float, default=0)
    final_price = db.Column(db.Float, nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    category = db.Column(db.String(50))

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')
    payment_method = db.Column(db.String(50))
    delivery_address = db.Column(db.Text)
    items_json = db.Column(db.Text)
    user = db.relationship('User', backref='orders')

class Cart(db.Model):
    __tablename__ = 'cart'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    item_id = db.Column(db.Integer, nullable=False)
    item_type = db.Column(db.String(20))
    item_name = db.Column(db.String(100))
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, default=1)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='cart_items')

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sender = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    user = db.relationship('User', backref='messages')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ===================== ROUTES =====================
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    mobile = data.get('mobile', '').strip()
    password = data.get('password', '')
    
    user = User.query.filter_by(mobile=mobile).first()
    
    if not user:
        # Auto redirect to register page for new user
        return jsonify({
            'success': False, 
            'message': 'No account found. Please register first.',
            'redirect_to_register': True,
            'mobile': mobile
        })
    
    if not check_password_hash(user.password, password):
        return jsonify({'success': False, 'message': 'Incorrect password'})
    
    login_user(user)
    return jsonify({'success': True})

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    required = ['name', 'mobile', 'password', 'confirm_password']
    for field in required:
        if not data.get(field):
            return jsonify({'success': False, 'message': f'{field.replace("_", " ").title()} required'})
    
    if data['password'] != data['confirm_password']:
        return jsonify({'success': False, 'message': 'Passwords do not match'})
    
    # Check if user already exists
    existing_user = User.query.filter_by(mobile=data['mobile']).first()
    if existing_user:
        return jsonify({
            'success': False, 
            'message': 'Mobile number already registered. Please login.',
            'redirect_to_login': True
        })
    
    if data.get('email'):
        existing_email = User.query.filter_by(email=data['email']).first()
        if existing_email:
            return jsonify({
                'success': False, 
                'message': 'Email already registered. Please login.',
                'redirect_to_login': True
            })
    
    user = User(
        name=data['name'],
        mobile=data['mobile'],
        email=data.get('email'),
        location=data.get('location', ''),
        profile_pic=data.get('profile_pic', ''),
        password=generate_password_hash(data['password'])
    )
    
    db.session.add(user)
    db.session.commit()
    
    msg = Message(
        user_id=user.id,
        sender='BiteBuddy',
        content=f'Welcome {user.name}! Enjoy your meals.'
    )
    db.session.add(msg)
    db.session.commit()
    
    login_user(user)
    return jsonify({'success': True})

@app.route('/dashboard')
@login_required
def dashboard():
    services = Service.query.filter_by(available=True).all()
    menu_items = Menu.query.all()
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.order_date.desc()).all()
    messages = Message.query.filter_by(user_id=current_user.id).order_by(Message.sent_at.desc()).limit(5).all()
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    
    cart_total = sum(item.price * item.quantity for item in cart_items)
    
    return render_template('dashboard.html',
                         services=services,
                         menu_items=menu_items,
                         orders=orders,
                         messages=messages,
                         cart_items=cart_items,
                         cart_count=len(cart_items),
                         cart_total=cart_total)

@app.route('/api/service/<int:service_id>')
@login_required
def get_service_details(service_id):
    service = Service.query.get(service_id)
    if not service:
        return jsonify({'error': 'Service not found'}), 404
    
    service_data = {
        'id': service.id,
        'name': service.name,
        'category': service.category,
        'base_price': service.base_price,
        'discount': service.discount,
        'final_price': service.final_price,
        'image_url': service.image_url,
        'description': service.description,
        'added_at': service.added_at.strftime('%d %b %Y, %I:%M %p'),
        'items': []
    }
    
    items = ServiceItem.query.filter_by(service_id=service_id).all()
    for item in items:
        service_data['items'].append({
            'id': item.id,
            'name': item.name,
            'image_url': item.image_url,
            'price': item.price,
            'description': item.description,
            'added_at': item.added_at.strftime('%d %b %Y')
        })
    
    return jsonify(service_data)

@app.route('/api/cart', methods=['GET', 'POST', 'DELETE'])
@login_required
def manage_cart():
    if request.method == 'GET':
        items = Cart.query.filter_by(user_id=current_user.id).all()
        cart_data = []
        for item in items:
            cart_data.append({
                'id': item.id,
                'item_id': item.item_id,
                'item_type': item.item_type,
                'name': item.item_name,
                'price': item.price,
                'quantity': item.quantity,
                'total': item.price * item.quantity
            })
        return jsonify(cart_data)
    
    elif request.method == 'POST':
        data = request.get_json()
        item_id = data.get('item_id')
        item_type = data.get('item_type')
        action = data.get('action', 'add')
        
        if item_type == 'service':
            item_obj = Service.query.get(item_id)
        else:
            item_obj = Menu.query.get(item_id)
        
        if not item_obj:
            return jsonify({'error': 'Item not found'}), 404
        
        cart_item = Cart.query.filter_by(
            user_id=current_user.id, 
            item_id=item_id, 
            item_type=item_type
        ).first()
        
        if action == 'add':
            if cart_item:
                cart_item.quantity += 1
            else:
                cart_item = Cart(
                    user_id=current_user.id,
                    item_id=item_id,
                    item_type=item_type,
                    item_name=item_obj.name,
                    price=item_obj.final_price,
                    quantity=1
                )
                db.session.add(cart_item)
        elif action == 'update':
            quantity = data.get('quantity', 1)
            if quantity <= 0:
                if cart_item:
                    db.session.delete(cart_item)
            else:
                if cart_item:
                    cart_item.quantity = quantity
                else:
                    cart_item = Cart(
                        user_id=current_user.id,
                        item_id=item_id,
                        item_type=item_type,
                        item_name=item_obj.name,
                        price=item_obj.final_price,
                        quantity=quantity
                    )
                    db.session.add(cart_item)
        
        db.session.commit()
        return jsonify({'success': True})
    
    elif request.method == 'DELETE':
        item_id = request.args.get('item_id')
        item_type = request.args.get('item_type')
        
        if item_id and item_type:
            Cart.query.filter_by(
                user_id=current_user.id, 
                item_id=item_id, 
                item_type=item_type
            ).delete()
        else:
            Cart.query.filter_by(user_id=current_user.id).delete()
        
        db.session.commit()
        return jsonify({'success': True})

@app.route('/api/order', methods=['POST'])
@login_required
def place_order():
    data = request.get_json()
    
    # Check if delivery location is provided
    delivery_address = data.get('address', '').strip()
    if not delivery_address:
        return jsonify({
            'success': False, 
            'message': 'Please provide delivery location using live location'
        }), 400
    
    # Check payment method - only Cash on Delivery available
    payment_method = data.get('payment_method', '')
    if payment_method != 'Cash on Delivery':
        return jsonify({
            'success': False,
            'message': 'Only Cash on Delivery available at the moment'
        }), 400
    
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        return jsonify({'error': 'Cart is empty'}), 400
    
    total = 0
    items_data = []
    for cart_item in cart_items:
        item_total = cart_item.price * cart_item.quantity
        total += item_total
        items_data.append({
            'id': cart_item.item_id,
            'type': cart_item.item_type,
            'name': cart_item.item_name,
            'price': cart_item.price,
            'quantity': cart_item.quantity,
            'total': item_total
        })
    
    order = Order(
        user_id=current_user.id,
        total_amount=total,
        payment_method=payment_method,
        delivery_address=delivery_address,
        items_json=json.dumps(items_data)
    )
    
    db.session.add(order)
    Cart.query.filter_by(user_id=current_user.id).delete()
    
    msg = Message(
        user_id=current_user.id,
        sender='Order System',
        content=f'Order #{order.id} confirmed. Total: ₹{total}. Will be delivered to: {delivery_address}'
    )
    db.session.add(msg)
    
    db.session.commit()
    
    return jsonify({'success': True, 'order_id': order.id})

@app.route('/api/get-location', methods=['POST'])
@login_required
def get_location():
    # This endpoint simulates getting location
    # In real app, you would get actual coordinates and convert to address
    return jsonify({
        'success': True,
        'location': 'Current Location Detected'
    })

@app.route('/api/messages')
@login_required
def get_messages():
    messages = Message.query.filter_by(user_id=current_user.id).order_by(Message.sent_at.desc()).all()
    messages_data = [{
        'id': m.id,
        'sender': m.sender,
        'content': m.content,
        'time': m.sent_at.strftime('%I:%M %p'),
        'date': m.sent_at.strftime('%d %b'),
        'is_read': m.is_read
    } for m in messages]
    
    for msg in Message.query.filter_by(user_id=current_user.id, is_read=False):
        msg.is_read = True
    db.session.commit()
    
    return jsonify(messages_data)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Initialize database
@app.route('/init-db')
def init_db():
    db.create_all()
    return "Database tables created successfully."

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
