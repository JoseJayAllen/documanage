from flask import Flask, request, jsonify, send_from_directory, redirect, url_for, send_file
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import uuid

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__,
            static_folder=BASE_DIR,
            static_url_path='',
            template_folder=BASE_DIR)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'documanage-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'mysql+mysqlconnector://root:root@localhost:3306/documanage'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['AVATAR_FOLDER'] = os.path.join(BASE_DIR, 'static', 'avatars')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Ensure upload directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['AVATAR_FOLDER'], exist_ok=True)

CORS(app, supports_credentials=True, origins=["http://localhost:5000", "http://127.0.0.1:5000", "*"])

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'serve_login'


@login_manager.unauthorized_handler
def unauthorized_callback():
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': 'Please log in'}), 401
    return redirect(url_for('serve_login', next=request.url))


@app.after_request
def add_cache_headers(response):
    """Add cache-control headers to prevent back-button access after logout"""
    # Add cache-busting headers for protected pages
    if request.endpoint in ['serve_index', 'serve_accounts', 'serve_profile', 'serve_history', 'serve_home']:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response


# ====================== MODELS ======================
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='viewer')
    department = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    id_number = db.Column(db.String(50), unique=True)
    status = db.Column(db.String(20), default='pending')  # Changed default to 'pending'
    avatar = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def to_dict(self):
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'name': self.get_full_name(),
            'email': self.email,
            'role': self.role,
            'avatar': self.avatar or f"https://ui-avatars.com/api/?name={self.first_name}+{self.last_name}&background=4e73df&color=fff",
            'status': self.status,
            'department': self.department,
            'phone': self.phone,
            'id_number': self.id_number,
            'created_at': self.created_at.strftime('%Y-%m-%d') if self.created_at else None,
            'last_login': self.last_login.strftime('%Y-%m-%d %H:%M') if self.last_login else None
        }


class File(db.Model):
    __tablename__ = 'files'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50))
    file_size = db.Column(db.String(20))
    file_path = db.Column(db.String(500), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    owner = db.relationship('User', backref='files')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.original_filename,
            'type': self.file_type,
            'size': self.file_size,
            'date': self.uploaded_at.strftime('%Y-%m-%d'),
            'user': self.owner.get_full_name() if self.owner else 'Unknown'
        }


class AuditTrail(db.Model):
    __tablename__ = 'audit_trails'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='audit_trails')

    def to_dict(self):
        return {
            'id': self.id,
            'action': self.action,
            'description': self.description,
            'user': self.user.get_full_name() if self.user else 'System',
            'time': self.created_at.strftime('%Y-%m-%d %H:%M'),
            'type': self.get_action_type()
        }

    def get_action_type(self):
        action_types = {
            'LOGIN': 'login',
            'LOGOUT': 'login',
            'REGISTER': 'success',
            'UPLOAD': 'success',
            'DELETE': 'danger',
            'SHARE': 'warning',
            'UPDATE': 'info',
            'CREATE_ACCOUNT': 'success',
            'ACTIVATE_ACCOUNT': 'success',
            'DEACTIVATE_ACCOUNT': 'danger'
        }
        return action_types.get(self.action, 'info')


# ====================== HELPERS ======================
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def generate_unique_id_number():
    """Generate a unique employee ID number"""
    import random
    year = datetime.now().year
    # Use timestamp + random to ensure uniqueness
    timestamp = datetime.now().strftime('%m%d%H%M%S')
    random_suffix = random.randint(10, 99)
    return f"EMP-{year}-{timestamp}{random_suffix}"


def log_audit(action, description, user_id=None):
    """Log an audit trail entry"""
    audit = AuditTrail(
        user_id=user_id or (current_user.id if current_user.is_authenticated else None),
        action=action,
        description=description,
        ip_address=request.remote_addr
    )
    db.session.add(audit)
    db.session.commit()


def calculate_storage_used():
    """Calculate actual storage used from database"""
    total_size = 0
    files = File.query.all()
    for file in files:
        try:
            if os.path.exists(file.file_path):
                total_size += os.path.getsize(file.file_path)
        except:
            pass

    # Convert to human readable
    if total_size == 0:
        return "0 MB"
    elif total_size < 1024 * 1024 * 1024:
        return f"{total_size / (1024 * 1024):.1f} MB"
    else:
        return f"{total_size / (1024 * 1024 * 1024):.2f} GB"


def get_total_storage_mb():
    """Get total storage in MB (for dashboard)"""
    total_size = 0
    files = File.query.all()
    for file in files:
        try:
            if os.path.exists(file.file_path):
                total_size += os.path.getsize(file.file_path)
        except:
            pass
    return round(total_size / (1024 * 1024), 2)


# ====================== ROUTES ======================
@app.route('/')
def root():
    if current_user.is_authenticated:
        return redirect(url_for('serve_index'))
    return redirect(url_for('serve_login'))


@app.route('/login.html')
def serve_login():
    return send_from_directory(BASE_DIR, 'login.html')


@app.route('/register.html')
def serve_register():
    return send_from_directory(BASE_DIR, 'register.html')


@app.route('/index.html')
@login_required
def serve_index():
    return send_from_directory(BASE_DIR, 'index.html')


@app.route('/accounts.html')
@login_required
def serve_accounts():
    return send_from_directory(BASE_DIR, 'accounts.html')


@app.route('/profile.html')
@login_required
def serve_profile():
    return send_from_directory(BASE_DIR, 'profile.html')


@app.route('/history.html')
@login_required
def serve_history():
    return send_from_directory(BASE_DIR, 'history.html')


@app.route('/home.html')
@login_required
def serve_home():
    return send_from_directory(BASE_DIR, 'home.html')


# ====================== AUTH ======================
@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json()
    user = User.query.filter_by(email=data.get('email')).first()

    if not user:
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

    if not user.check_password(data.get('password')):
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

    if user.status == 'pending':
        return jsonify(
            {'success': False, 'message': 'Your account is pending approval. Please contact an administrator.'}), 403

    if user.status == 'inactive':
        return jsonify(
            {'success': False, 'message': 'Your account has been deactivated. Please contact an administrator.'}), 403

    if user.status == 'active':
        login_user(user, remember=True)
        user.last_login = datetime.utcnow()
        db.session.commit()
        log_audit('LOGIN', f'User {user.email} logged in')
        return jsonify({'success': True, 'user': user.to_dict()})

    return jsonify({'success': False, 'message': 'Account status error'}), 400


@app.route('/api/auth/register', methods=['POST'])
def api_register():
    data = request.get_json()
    if User.query.filter_by(email=data.get('email')).first():
        return jsonify({'success': False, 'message': 'Email already exists'}), 400

    new_user = User(
        first_name=data['first_name'],
        last_name=data['last_name'],
        email=data['email'],
        role=data.get('user_type', 'viewer'),
        department=data.get('department'),
        phone=data.get('phone'),
        status='pending',  # New accounts are pending by default
        id_number=data.get('id_number') or generate_unique_id_number()
    )
    new_user.set_password(data['password'])
    db.session.add(new_user)
    db.session.commit()

    # Log registration but DON'T auto-login
    log_audit('REGISTER', f'New user {new_user.email} registered (pending approval)', new_user.id)

    return jsonify({
        'success': True,
        'message': 'Registration successful! Your account is pending administrator approval.',
        'pending_approval': True
    })


@app.route('/api/auth/me')
@login_required
def api_current_user():
    return jsonify(current_user.to_dict())


@app.route('/api/auth/logout', methods=['POST'])
@login_required
def api_logout():
    log_audit('LOGOUT', f'User {current_user.email} logged out')
    logout_user()
    return jsonify({'success': True})


# ====================== PROFILE ======================
@app.route('/api/profile', methods=['GET', 'PUT'])
@login_required
def api_profile():
    if request.method == 'GET':
        return jsonify(current_user.to_dict())

    # PUT - Update profile
    data = request.get_json()
    current_user.first_name = data.get('first_name', current_user.first_name)
    current_user.last_name = data.get('last_name', current_user.last_name)
    current_user.phone = data.get('phone', current_user.phone)
    current_user.department = data.get('department', current_user.department)
    db.session.commit()
    log_audit('UPDATE', 'User updated profile information')
    return jsonify({'success': True, 'user': current_user.to_dict()})


@app.route('/api/profile/password', methods=['PUT'])
@login_required
def api_change_password():
    data = request.get_json()
    if not current_user.check_password(data.get('current_password')):
        return jsonify({'success': False, 'message': 'Current password is incorrect'}), 400

    if data.get('new_password') != data.get('confirm_password'):
        return jsonify({'success': False, 'message': 'New passwords do not match'}), 400

    current_user.set_password(data.get('new_password'))
    db.session.commit()
    log_audit('UPDATE', 'User changed password')
    return jsonify({'success': True, 'message': 'Password updated successfully'})


@app.route('/api/profile/avatar', methods=['POST'])
@login_required
def api_upload_avatar():
    if 'avatar' not in request.files:
        return jsonify({'success': False, 'message': 'No file provided'}), 400

    file = request.files['avatar']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400

    # Validate file type
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    if ext not in allowed_extensions:
        return jsonify({'success': False, 'message': 'Invalid file type. Allowed: PNG, JPG, JPEG, GIF'}), 400

    # Save file
    filename = f"avatar_{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(app.config['AVATAR_FOLDER'], filename)
    file.save(filepath)

    # Update user avatar
    current_user.avatar = f'/static/avatars/{filename}'
    db.session.commit()
    log_audit('UPDATE', 'User updated profile photo')

    return jsonify({'success': True, 'avatar': current_user.avatar})


# ====================== ACCOUNTS ======================
@app.route('/api/accounts', methods=['GET', 'POST'])
@login_required
def api_accounts():
    if current_user.role != 'admin':
        return jsonify({'error': 'Permission denied'}), 403

    if request.method == 'GET':
        users = User.query.all()
        return jsonify([u.to_dict() for u in users])

    # POST - Create new account
    data = request.get_json()
    if User.query.filter_by(email=data.get('email')).first():
        return jsonify({'error': 'Email already exists'}), 400

    new_user = User(
        first_name=data['first_name'],
        last_name=data['last_name'],
        email=data['email'],
        role=data.get('user_type', 'viewer'),
        department=data.get('department'),
        phone=data.get('phone'),
        status=data.get('status', 'active'),
        id_number=data.get('id_number') or generate_unique_id_number()
    )
    new_user.set_password(data.get('password', 'password123'))
    db.session.add(new_user)
    db.session.commit()
    log_audit('CREATE_ACCOUNT', f'Admin created account for {new_user.email}')
    return jsonify(new_user.to_dict()), 201


@app.route('/api/accounts/<int:user_id>', methods=['PUT', 'DELETE'])
@login_required
def api_account_detail(user_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Permission denied'}), 403

    user = User.query.get_or_404(user_id)

    if request.method == 'DELETE':
        if user.id == current_user.id:
            return jsonify({'error': 'Cannot delete your own account'}), 400
        db.session.delete(user)
        db.session.commit()
        log_audit('DELETE', f'Admin deleted account for {user.email}')
        return jsonify({'success': True, 'message': 'Account deleted'})

    # PUT - Update account
    data = request.get_json()
    old_status = user.status

    user.first_name = data.get('first_name', user.first_name)
    user.last_name = data.get('last_name', user.last_name)
    user.role = data.get('role', user.role)
    user.status = data.get('status', user.status)
    user.department = data.get('department', user.department)
    db.session.commit()

    # Log status change
    if old_status != user.status:
        if user.status == 'active':
            log_audit('ACTIVATE_ACCOUNT', f'Admin activated account for {user.email}')
        elif user.status == 'inactive':
            log_audit('DEACTIVATE_ACCOUNT', f'Admin deactivated account for {user.email}')
    else:
        log_audit('UPDATE', f'Admin updated account for {user.email}')

    return jsonify(user.to_dict())


@app.route('/api/accounts/<int:user_id>/activate', methods=['POST'])
@login_required
def api_activate_account(user_id):
    """Activate a pending or inactive account"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Permission denied'}), 403

    user = User.query.get_or_404(user_id)
    user.status = 'active'
    db.session.commit()
    log_audit('ACTIVATE_ACCOUNT', f'Admin activated account for {user.email}')

    return jsonify({'success': True, 'message': 'Account activated', 'user': user.to_dict()})


@app.route('/api/accounts/<int:user_id>/deactivate', methods=['POST'])
@login_required
def api_deactivate_account(user_id):
    """Deactivate an active account"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Permission denied'}), 403

    if user_id == current_user.id:
        return jsonify({'error': 'Cannot deactivate your own account'}), 400

    user = User.query.get_or_404(user_id)
    user.status = 'inactive'
    db.session.commit()
    log_audit('DEACTIVATE_ACCOUNT', f'Admin deactivated account for {user.email}')

    return jsonify({'success': True, 'message': 'Account deactivated', 'user': user.to_dict()})


# ====================== FILES ======================
@app.route('/api/files', methods=['GET', 'POST'])
@login_required
def api_files():
    if request.method == 'GET':
        files = File.query.order_by(File.uploaded_at.desc()).all()
        return jsonify([f.to_dict() for f in files])

    # POST - Upload file
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    filename = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
    file.save(path)

    # Get file extension
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'doc'
    file_type = 'pdf' if ext == 'pdf' else 'img' if ext in ['jpg', 'jpeg', 'png', 'gif'] else 'xls' if ext in ['xls',
                                                                                                               'xlsx'] else 'doc'

    new_file = File(
        filename=unique_name,
        original_filename=filename,
        file_type=file_type,
        file_size=f"{os.path.getsize(path) / (1024 * 1024):.2f} MB",
        file_path=path,
        user_id=current_user.id
    )
    db.session.add(new_file)
    db.session.commit()
    log_audit('UPLOAD', f'Uploaded {filename}')
    return jsonify(new_file.to_dict()), 201


@app.route('/api/files/<int:file_id>', methods=['DELETE'])
@login_required
def api_delete_file(file_id):
    file = File.query.get_or_404(file_id)

    # Check permissions (only admin, editor who uploaded, or file owner can delete)
    if current_user.role == 'viewer':
        return jsonify({'error': 'Permission denied'}), 403

    if current_user.role == 'editor' and file.user_id != current_user.id:
        return jsonify({'error': 'Can only delete your own files'}), 403

    # Delete physical file
    try:
        if os.path.exists(file.file_path):
            os.remove(file.file_path)
    except Exception as e:
        print(f"Error deleting file: {e}")

    # Delete database record
    filename = file.original_filename
    db.session.delete(file)
    db.session.commit()
    log_audit('DELETE', f'Deleted file {filename}')

    return jsonify({'success': True, 'message': 'File deleted'})


@app.route('/api/files/<int:file_id>/download')
@login_required
def api_download_file(file_id):
    file = File.query.get_or_404(file_id)
    if os.path.exists(file.file_path):
        log_audit('DOWNLOAD', f'Downloaded {file.original_filename}')
        return send_file(file.file_path, as_attachment=True, download_name=file.original_filename)
    return jsonify({'error': 'File not found on server'}), 404


@app.route('/api/files/<int:file_id>/preview')
@login_required
def api_preview_file(file_id):
    file = File.query.get_or_404(file_id)
    if os.path.exists(file.file_path):
        # Serve inline so browser can preview (PDF opens in viewer, images show, etc.)
        return send_file(file.file_path, as_attachment=False, download_name=file.original_filename)
    return jsonify({'error': 'File not found'}), 404

# ====================== AUDIT TRAIL ======================
@app.route('/api/audit-trail')
@login_required
def api_audit_trail():
    # Get query parameters for filtering
    date_range = request.args.get('date_range', 'all')
    activity_type = request.args.get('activity_type', 'all')
    user_filter = request.args.get('user', 'all')

    query = AuditTrail.query

    # Apply date filter
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if start_date and end_date:
        # Custom date range from calendar picker
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)  # Include the end date
            query = query.filter(AuditTrail.created_at >= start, AuditTrail.created_at < end)
        except ValueError:
            pass  # Invalid date format, ignore
    elif date_range == 'today':
        today = datetime.now().date()
        query = query.filter(db.func.date(AuditTrail.created_at) == today)
    elif date_range == 'week':
        week_ago = datetime.now() - timedelta(days=7)
        query = query.filter(AuditTrail.created_at >= week_ago)
    elif date_range == 'month':
        month_ago = datetime.now() - timedelta(days=30)
        query = query.filter(AuditTrail.created_at >= month_ago)
    elif date_range == 'year':
        year_ago = datetime.now() - timedelta(days=365)
        query = query.filter(AuditTrail.created_at >= year_ago)

    # Apply activity type filter
    if activity_type != 'all':
        action_map = {
            'upload': 'UPLOAD',
            'download': 'DOWNLOAD',
            'delete': 'DELETE',
            'share': 'SHARE',
            'login': 'LOGIN',
            'logout': 'LOGOUT',
            'register': 'REGISTER',
            'update': 'UPDATE',
            'create_account': 'CREATE_ACCOUNT',
            'activate': 'ACTIVATE_ACCOUNT',
            'deactivate': 'DEACTIVATE_ACCOUNT'
        }
        if activity_type in action_map:
            query = query.filter(AuditTrail.action == action_map[activity_type])

    # Apply user filter
    if user_filter != 'all':
        query = query.filter(AuditTrail.user_id == int(user_filter))

    trails = query.order_by(AuditTrail.created_at.desc()).limit(200).all()
    return jsonify([t.to_dict() for t in trails])


@app.route('/api/audit-trail/stats')
@login_required
def api_audit_stats():
    today = datetime.now().date()
    week_ago = datetime.now() - timedelta(days=7)

    total = AuditTrail.query.count()
    uploads = AuditTrail.query.filter_by(action='UPLOAD').count()
    downloads = AuditTrail.query.filter_by(action='DOWNLOAD').count()
    today_logins = AuditTrail.query.filter(
        AuditTrail.action == 'LOGIN',
        db.func.date(AuditTrail.created_at) == today
    ).count()

    # Get activity breakdown for summary
    all_actions = db.session.query(AuditTrail.action, db.func.count(AuditTrail.id)).group_by(AuditTrail.action).all()
    action_breakdown = {action: count for action, count in all_actions}

    return jsonify({
        'total_activities': total,
        'uploads': uploads,
        'downloads': downloads,
        'today_logins': today_logins,
        'action_breakdown': action_breakdown
    })


@app.route('/api/audit-trail/recent-logins')
@login_required
def api_recent_logins():
    """Recent logins available to all users"""
    recent_logins = AuditTrail.query.filter(
        AuditTrail.action.in_(['LOGIN', 'LOGOUT'])
    ).order_by(AuditTrail.created_at.desc()).limit(10).all()

    return jsonify([{
        'id': log.id,
        'user': log.user.get_full_name() if log.user else 'System',
        'avatar': log.user.avatar if log.user and log.user.avatar else f"https://ui-avatars.com/api/?name={log.user.first_name}+{log.user.last_name}&background=4e73df&color=fff" if log.user else None,
        'action': log.action,
        'time': log.created_at.strftime('%Y-%m-%d %H:%M'),
        'time_relative': get_relative_time(log.created_at)
    } for log in recent_logins])


def get_relative_time(dt):
    """Convert datetime to relative time string"""
    now = datetime.utcnow()
    diff = now - dt

    if diff.days == 0:
        if diff.seconds < 60:
            return 'Just now'
        elif diff.seconds < 3600:
            return f'{diff.seconds // 60} minutes ago'
        else:
            return f'{diff.seconds // 3600} hours ago'
    elif diff.days == 1:
        return 'Yesterday'
    elif diff.days < 7:
        return f'{diff.days} days ago'
    else:
        return dt.strftime('%Y-%m-%d')


# ====================== STATS ======================
@app.route('/api/stats')
@login_required
def api_stats():
    total_files = File.query.count()
    total_users = User.query.filter_by(status='active').count()
    storage_mb = get_total_storage_mb()
    recent_activity = AuditTrail.query.filter(
        AuditTrail.created_at >= datetime.now() - timedelta(days=7)
    ).count()

    return jsonify({
        'total_files': total_files,
        'total_users': total_users,
        'storage_used': f"{storage_mb} MB",
        'storage_mb': storage_mb,
        'recent_activity': recent_activity
    })


@app.route('/api/accounts/stats')
@login_required
def api_accounts_stats():
    if current_user.role != 'admin':
        return jsonify({'error': 'Permission denied'}), 403

    total = User.query.count()
    active = User.query.filter_by(status='active').count()
    inactive = User.query.filter_by(status='inactive').count()
    pending = User.query.filter_by(status='pending').count()
    admins = User.query.filter_by(role='admin').count()

    return jsonify({
        'total_accounts': total,
        'active_users': active,
        'inactive_users': inactive,
        'pending_accounts': pending,
        'administrators': admins
    })




class Announcement(db.Model):
    __tablename__ = 'announcements'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='general')  # general, weekly_report, announcement, update
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    author = db.relationship('User', backref='announcements')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'category': self.category,
            'author': self.author.get_full_name() if self.author else 'System',
            'author_avatar': self.author.avatar if self.author and self.author.avatar else f"https://ui-avatars.com/api/?name={self.author.first_name}+{self.author.last_name}&background=4e73df&color=fff" if self.author else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
            'date': self.created_at.strftime('%B %d, %Y') if self.created_at else None,
            'time_ago': get_relative_time(self.created_at)
        }




# ====================== ANNOUNCEMENTS / HOME FEED ======================
@app.route('/api/announcements', methods=['GET', 'POST'])
@login_required
def api_announcements():
    if request.method == 'GET':
        category = request.args.get('category', 'all')
        query = Announcement.query
        if category != 'all':
            query = query.filter_by(category=category)
        announcements = query.order_by(Announcement.created_at.desc()).limit(50).all()
        return jsonify([a.to_dict() for a in announcements])

    # POST - Create announcement (admin/editor only)
    if current_user.role == 'viewer':
        return jsonify({'error': 'Permission denied'}), 403

    data = request.get_json()
    new_announcement = Announcement(
        title=data['title'],
        content=data['content'],
        category=data.get('category', 'general'),
        author_id=current_user.id
    )
    db.session.add(new_announcement)
    db.session.commit()
    log_audit('CREATE_ANNOUNCEMENT', f'Created announcement: {new_announcement.title}')
    return jsonify(new_announcement.to_dict()), 201


@app.route('/api/announcements/<int:ann_id>', methods=['PUT', 'DELETE'])
@login_required
def api_announcement_detail(ann_id):
    announcement = Announcement.query.get_or_404(ann_id)

    if request.method == 'DELETE':
        if current_user.role not in ['admin', 'editor']:
            return jsonify({'error': 'Permission denied'}), 403
        db.session.delete(announcement)
        db.session.commit()
        log_audit('DELETE', f'Deleted announcement: {announcement.title}')
        return jsonify({'success': True, 'message': 'Announcement deleted'})

    # PUT - Update
    if current_user.role not in ['admin', 'editor']:
        return jsonify({'error': 'Permission denied'}), 403

    data = request.get_json()
    announcement.title = data.get('title', announcement.title)
    announcement.content = data.get('content', announcement.content)
    announcement.category = data.get('category', announcement.category)
    db.session.commit()
    log_audit('UPDATE', f'Updated announcement: {announcement.title}')
    return jsonify(announcement.to_dict())


@app.route('/api/home/stats')
@login_required
def api_home_stats():
    """Get statistics for the Home page"""
    total_files = File.query.count()
    total_users = User.query.filter_by(status='active').count()
    storage_mb = get_total_storage_mb()
    recent_activity = AuditTrail.query.filter(
        AuditTrail.created_at >= datetime.now() - timedelta(days=7)
    ).count()
    total_announcements = Announcement.query.count()

    return jsonify({
        'total_files': total_files,
        'total_users': total_users,
        'storage_used': f"{storage_mb} MB",
        'storage_mb': storage_mb,
        'recent_activity': recent_activity,
        'total_announcements': total_announcements
    })

# ====================== NOTIFICATIONS (PLACEHOLDER) ======================
@app.route('/api/notifications')
@login_required
def api_notifications():
    # Return empty array for now - can be expanded later
    return jsonify([])


@app.route('/api/notifications/unread-count')
@login_required
def api_notification_count():
    return jsonify({'count': 0})


@app.route('/api/messages')
@login_required
def api_messages():
    # Return empty array for now - can be expanded later
    return jsonify([])


@app.route('/api/messages/unread-count')
@login_required
def api_message_count():
    return jsonify({'count': 0})


# ====================== INITIALIZATION ======================
def create_default_data():
    """Create default users if none exist"""
    if User.query.count() == 0:
        print("Creating default users...")

        # Create admin user
        admin = User(
            first_name='Admin',
            last_name='User',
            email='admin@documanage.com',
            role='admin',
            department='Administration',
            status='active',
            id_number=f"EMP-{datetime.now().year}-001"
        )
        admin.set_password('admin123')
        db.session.add(admin)

        # Create editor user
        editor = User(
            first_name='Editor',
            last_name='User',
            email='editor@documanage.com',
            role='editor',
            department='Operations',
            status='active',
            id_number=f"EMP-{datetime.now().year}-002"
        )
        editor.set_password('editor123')
        db.session.add(editor)

        # Create viewer user
        viewer = User(
            first_name='Viewer',
            last_name='User',
            email='viewer@documanage.com',
            role='viewer',
            department='Operations',
            status='active',
            id_number=f"EMP-{datetime.now().year}-003"
        )
        viewer.set_password('viewer123')
        db.session.add(viewer)

        db.session.commit()
        print("Default users created!")

    # Create sample announcements if none exist
    if Announcement.query.count() == 0:
        print("Creating sample announcements...")

        # Get admin user for author
        admin_user = User.query.filter_by(email='admin@documanage.com').first()
        editor_user = User.query.filter_by(email='editor@documanage.com').first()

        announcements = [
            Announcement(
                title='Welcome to DocuManage v2.0!',
                content='We are excited to announce the launch of DocuManage v2.0. This new version includes a brand new Home page with announcements, improved search functionality, calendar-based audit reports, and a refreshed user interface. Thank you for choosing DocuManage for your document management needs.',
                category='announcement',
                author_id=admin_user.id if admin_user else None
            ),
            Announcement(
                title='Weekly Report - System Performance',
                content='This week our system achieved 99.9% uptime. We processed over 1,250 file uploads and 3,400 downloads. Storage usage is at 42% capacity. No critical issues were reported. The new calendar reporting feature has been successfully deployed.',
                category='weekly_report',
                author_id=editor_user.id if editor_user else None
            ),
            Announcement(
                title='New Feature: Calendar-Based Reports',
                content='We have added a new calendar feature to the Audit Trail page. You can now select specific date ranges (single day, week, or month) to generate detailed activity reports. These reports can be printed or downloaded as CSV files for your records.',
                category='update',
                author_id=admin_user.id if admin_user else None
            ),
            Announcement(
                title='Security Update - Enhanced Password Policy',
                content='As part of our ongoing commitment to security, we have enhanced our password policies. All users are encouraged to update their passwords to meet the new minimum requirements: at least 8 characters including uppercase, lowercase, and numbers.',
                category='announcement',
                author_id=admin_user.id if admin_user else None
            ),
            Announcement(
                title='General: Document Retention Policy Reminder',
                content='Please remember that all documents stored in DocuManage are subject to our retention policy. Inactive files older than 2 years may be archived. Please review your files and ensure important documents are properly categorized.',
                category='general',
                author_id=editor_user.id if editor_user else None
            )
        ]

        for ann in announcements:
            db.session.add(ann)

        db.session.commit()
        print("Sample announcements created!")


# ====================== RUN ======================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_default_data()
    print("DocuManage running at http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)