from flask import Flask, request, jsonify, send_from_directory, redirect, url_for, send_file
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, timezone
import pytz
import os
import uuid
import re  # NEW: for bio sanitization

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__,
            static_folder=BASE_DIR,
            static_url_path='',
            template_folder=BASE_DIR)

# Configuration
app.config.from_object('config.Config')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'oqaadms-secret-key-change-in-production')
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['AVATAR_FOLDER'] = os.path.join(BASE_DIR, 'static', 'avatars')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB for video and large file support

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
    if request.endpoint in ['serve_index', 'serve_accounts', 'serve_profile', 'serve_history', 'serve_home']:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response


# ====================== TIMEZONE HELPERS ======================
# All timestamps are stored in UTC but displayed in Asia/Manila (UTC+8)

MANILA_TZ = pytz.timezone('Asia/Manila')


def now_utc():
    """Return current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def to_manila(dt):
    """Convert any datetime to Asia/Manila timezone for display."""
    if dt is None:
        return None
    # Ensure timezone-aware (assume UTC if naive)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(MANILA_TZ)


def format_datetime(dt, fmt='%Y-%m-%d %H:%M'):
    """Safely format a datetime object in Manila time."""
    if dt is None:
        return None
    manila_dt = to_manila(dt)
    return manila_dt.strftime(fmt)


def format_date(dt, fmt='%Y-%m-%d'):
    """Safely format a date/datetime to date string in Manila time."""
    if dt is None:
        return None
    manila_dt = to_manila(dt)
    return manila_dt.strftime(fmt)


def parse_date(date_str, fmt='%Y-%m-%d'):
    """Parse a date string to timezone-aware datetime (start of day in Manila, stored as UTC)."""
    if not date_str:
        return None
    try:
        naive = datetime.strptime(date_str, fmt)
        # Localize to Manila then convert to UTC for storage
        manila_dt = MANILA_TZ.localize(naive)
        return manila_dt.astimezone(timezone.utc)
    except ValueError:
        return None


# ====================== FILE TYPE HELPERS ======================
# Comprehensive file type classification and validation

ALLOWED_EXTENSIONS = {
    'image': {'jpg', 'jpeg', 'png', 'gif', 'webp'},
    'video': {'mp4', 'mov', 'avi', 'mkv', 'webm'},
    'document': {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt'},
    'archive': {'zip', 'rar', '7z'}
}
ALL_ALLOWED_EXTENSIONS = set().union(*ALLOWED_EXTENSIONS.values())


def get_file_type(ext):
    """Classify file extension into a type category for UI rendering."""
    ext = ext.lower()
    if ext in ALLOWED_EXTENSIONS['image']:
        return 'img'
    elif ext in ALLOWED_EXTENSIONS['video']:
        return 'video'
    elif ext in ALLOWED_EXTENSIONS['document']:
        if ext == 'pdf':
            return 'pdf'
        elif ext in ['xls', 'xlsx']:
            return 'xls'
        elif ext in ['ppt', 'pptx']:
            return 'ppt'
        else:
            return 'doc'
    elif ext in ALLOWED_EXTENSIONS['archive']:
        return 'archive'
    return 'other'


# ====================== MODELS ======================
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user')
    department = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    id_number = db.Column(db.String(50), unique=True)
    status = db.Column(db.String(20), default='pending')
    avatar = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=now_utc)
    last_login = db.Column(db.DateTime)
    bio = db.Column(db.Text)  # NEW: User biography

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
            'created_at': format_date(self.created_at),
            'last_login': format_datetime(self.last_login),
            'bio': self.bio or ''  # NEW
        }


class Folder(db.Model):
    __tablename__ = 'folders'
    id = db.Column(db.Integer, primary_key=True)
    folder_name = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=now_utc)
    updated_at = db.Column(db.DateTime, default=now_utc, onupdate=now_utc)

    user = db.relationship('User', backref='folders')
    files = db.relationship('File', backref='folder', lazy='dynamic')

    def to_dict(self, file_count=None):
        # file_count can be passed from an optimized query to avoid N+1 issues
        return {
            'id': self.id,
            'folder_name': self.folder_name,
            'user_id': self.user_id,
            'owner_name': self.user.get_full_name() if self.user else 'Unknown',
            'file_count': file_count if file_count is not None else self.files.count(),
            'created_at': format_date(self.created_at),
            'updated_at': format_datetime(self.updated_at)
        }


class File(db.Model):
    __tablename__ = 'files'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50))
    file_size = db.Column(db.String(20))
    file_path = db.Column(db.String(500), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=now_utc)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    folder_id = db.Column(db.Integer, db.ForeignKey('folders.id'), nullable=True)

    owner = db.relationship('User', backref='files')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.original_filename,
            'type': self.file_type,
            'size': self.file_size,
            'date': format_date(self.uploaded_at),
            'user_id': self.user_id,
            'user': self.owner.get_full_name() if self.owner else 'Unknown',
            'folder_id': self.folder_id,
            'folder_name': self.folder.folder_name if self.folder else 'Uncategorized'
        }


class AuditTrail(db.Model):
    __tablename__ = 'audit_trails'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=now_utc)

    user = db.relationship('User', backref='audit_trails')

    def to_dict(self):
        return {
            'id': self.id,
            'action': self.action,
            'description': self.description,
            'user': self.user.get_full_name() if self.user else 'System',
            'user_role': self.user.role if self.user else 'system',
            'time': format_datetime(self.created_at),
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
            'DEACTIVATE_ACCOUNT': 'danger',
            'CREATE_ANNOUNCEMENT': 'success',
            'CREATE_FOLDER': 'success',
            'UPDATE_FOLDER': 'info',
            'DELETE_FOLDER': 'danger'
        }
        return action_types.get(self.action, 'info')


class Announcement(db.Model):
    __tablename__ = 'announcements'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='general')
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=now_utc)
    updated_at = db.Column(db.DateTime, default=now_utc, onupdate=now_utc)

    author = db.relationship('User', backref='announcements')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'category': self.category,
            'author': self.author.get_full_name() if self.author else 'System',
            'author_avatar': self.author.avatar if self.author and self.author.avatar else f"https://ui-avatars.com/api/?name={self.author.first_name}+{self.author.last_name}&background=4e73df&color=fff" if self.author else None,
            'created_at': format_datetime(self.created_at),
            'date': format_date(self.created_at, '%B %d, %Y'),
            'time_ago': get_relative_time(self.created_at)
        }


# ====================== HELPERS ======================
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def generate_unique_id_number():
    """Generate a unique employee ID number"""
    import random
    year = datetime.now(timezone.utc).year
    timestamp = datetime.now(timezone.utc).strftime('%m%d%H%M%S')
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


def get_relative_time(dt):
    """Convert datetime to relative time string using Manila timezone."""
    if dt is None:
        return 'Unknown'
    now = datetime.now(timezone.utc)
    # Ensure dt is timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    # Convert both to Manila for accurate relative time
    manila_now = now.astimezone(MANILA_TZ)
    manila_dt = dt.astimezone(MANILA_TZ)
    diff = manila_now - manila_dt

    if diff.days < 0:
        return 'Just now'
    if diff.days == 0:
        if diff.seconds < 60:
            return 'Just now'
        elif diff.seconds < 3600:
            mins = diff.seconds // 60
            return f'{mins} minute{"s" if mins != 1 else ""} ago'
        else:
            hrs = diff.seconds // 3600
            return f'{hrs} hour{"s" if hrs != 1 else ""} ago'
    elif diff.days == 1:
        return 'Yesterday'
    elif diff.days < 7:
        return f'{diff.days} day{"s" if diff.days != 1 else ""} ago'
    elif diff.days < 30:
        weeks = diff.days // 7
        return f'{weeks} week{"s" if weeks != 1 else ""} ago'
    else:
        return format_date(dt)


# NEW: Bio sanitization helper
def sanitize_bio(text):
    """Remove HTML tags and trim whitespace from bio text."""
    if not text:
        return ''
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()


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
        user.last_login = now_utc()
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
        role=data.get('user_type', 'user'),
        department=data.get('department'),
        phone=data.get('phone'),
        status='pending',
        id_number=data.get('id_number') or generate_unique_id_number()
    )
    new_user.set_password(data['password'])
    db.session.add(new_user)
    db.session.commit()

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

    data = request.get_json()
    current_user.first_name = data.get('first_name', current_user.first_name)
    current_user.last_name = data.get('last_name', current_user.last_name)
    current_user.phone = data.get('phone', current_user.phone)
    current_user.department = data.get('department', current_user.department)
    if data.get('id_number'):
        current_user.id_number = data.get('id_number')

    # NEW: Bio validation and sanitization
    if 'bio' in data:
        bio = sanitize_bio(data['bio'])
        if len(bio) > 500:
            return jsonify({'success': False, 'message': 'Bio must not exceed 500 characters'}), 400
        current_user.bio = bio if bio else None

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

    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    if ext not in allowed_extensions:
        return jsonify({'success': False, 'message': 'Invalid file type. Allowed: PNG, JPG, JPEG, GIF'}), 400

    filename = f"avatar_{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(app.config['AVATAR_FOLDER'], filename)
    file.save(filepath)

    current_user.avatar = f'/static/avatars/{filename}'
    db.session.commit()
    log_audit('UPDATE', 'User updated profile photo')

    return jsonify({'success': True, 'avatar': current_user.avatar})


@app.route('/api/profile/avatar', methods=['DELETE'])
@login_required
def api_delete_avatar():
    if current_user.avatar:
        avatar_path = os.path.join(BASE_DIR, current_user.avatar.lstrip('/'))
        try:
            if os.path.exists(avatar_path):
                os.remove(avatar_path)
        except Exception as e:
            print(f"Error removing avatar file: {e}")
    current_user.avatar = None
    db.session.commit()
    log_audit('UPDATE', 'User removed profile photo')
    return jsonify({'success': True, 'message': 'Profile photo removed'})


# ====================== ACCOUNTS ======================
@app.route('/api/accounts', methods=['GET', 'POST'])
@login_required
def api_accounts():
    if current_user.role != 'admin':
        return jsonify({'error': 'Permission denied'}), 403

    if request.method == 'GET':
        users = User.query.all()
        return jsonify([u.to_dict() for u in users])

    data = request.get_json()
    if User.query.filter_by(email=data.get('email')).first():
        return jsonify({'error': 'Email already exists'}), 400

    new_user = User(
        first_name=data['first_name'],
        last_name=data['last_name'],
        email=data['email'],
        role=data.get('user_type', 'user'),
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

    data = request.get_json()
    old_status = user.status

    user.first_name = data.get('first_name', user.first_name)
    user.last_name = data.get('last_name', user.last_name)
    user.role = data.get('role', user.role)
    user.status = data.get('status', user.status)
    user.department = data.get('department', user.department)
    db.session.commit()

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
    if current_user.role != 'admin':
        return jsonify({'error': 'Permission denied'}), 403

    if user_id == current_user.id:
        return jsonify({'error': 'Cannot deactivate your own account'}), 400

    user = User.query.get_or_404(user_id)
    user.status = 'inactive'
    db.session.commit()
    log_audit('DEACTIVATE_ACCOUNT', f'Admin deactivated account for {user.email}')

    return jsonify({'success': True, 'message': 'Account deactivated', 'user': user.to_dict()})


# ====================== FOLDERS ======================
@app.route('/api/folders', methods=['GET'])
@login_required
def api_folders():
    """Get all folders with accurate, database-driven file counts.
    Uses a single optimized query with outer join to avoid N+1 performance issues.
    """
    from sqlalchemy import func
    folders_with_counts = db.session.query(
        Folder,
        func.count(File.id).label('file_count')
    ).outerjoin(File, Folder.id == File.folder_id).group_by(Folder.id).order_by(Folder.created_at.desc()).all()

    return jsonify([f.to_dict(file_count=count) for f, count in folders_with_counts])


@app.route('/api/folders/create', methods=['POST'])
@login_required
def api_create_folder():
    """Create a new folder"""
    data = request.get_json()
    name = data.get('folder_name', '').strip()

    if not name:
        return jsonify({'success': False, 'message': 'Folder name cannot be empty'}), 400

    if len(name) > 255:
        return jsonify({'success': False, 'message': 'Folder name too long (max 255 characters)'}), 400

    # Check for duplicates per user
    existing = Folder.query.filter_by(user_id=current_user.id, folder_name=name).first()
    if existing:
        return jsonify({'success': False, 'message': 'Folder name already exists'}), 400

    folder = Folder(
        folder_name=name,
        user_id=current_user.id
    )
    db.session.add(folder)
    db.session.commit()
    log_audit('CREATE_FOLDER', f'Created folder: {name}')
    return jsonify({'success': True, 'folder': folder.to_dict()}), 201


@app.route('/api/folders/update/<int:folder_id>', methods=['PUT'])
@login_required
def api_update_folder(folder_id):
    """Rename a folder"""
    folder = Folder.query.get_or_404(folder_id)

    # Verify ownership
    if folder.user_id != current_user.id and current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    data = request.get_json()
    new_name = data.get('folder_name', '').strip()

    if not new_name:
        return jsonify({'success': False, 'message': 'Folder name cannot be empty'}), 400

    if len(new_name) > 255:
        return jsonify({'success': False, 'message': 'Folder name too long (max 255 characters)'}), 400

    # Check for duplicates (excluding self)
    existing = Folder.query.filter(
        Folder.user_id == current_user.id,
        Folder.folder_name == new_name,
        Folder.id != folder_id
    ).first()
    if existing:
        return jsonify({'success': False, 'message': 'Folder name already exists'}), 400

    old_name = folder.folder_name
    folder.folder_name = new_name
    folder.updated_at = now_utc()
    db.session.commit()
    log_audit('UPDATE_FOLDER', f'Renamed folder from "{old_name}" to "{new_name}"')
    return jsonify({'success': True, 'folder': folder.to_dict()})


@app.route('/api/folders/delete/<int:folder_id>', methods=['DELETE'])
@login_required
def api_delete_folder(folder_id):
    """Delete a folder and move files to Uncategorized"""
    folder = Folder.query.get_or_404(folder_id)

    # Verify ownership
    if folder.user_id != current_user.id and current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    # Move files to Uncategorized (folder_id = None)
    files_in_folder = File.query.filter_by(folder_id=folder_id).all()
    for f in files_in_folder:
        f.folder_id = None

    folder_name = folder.folder_name
    db.session.delete(folder)
    db.session.commit()
    log_audit('DELETE_FOLDER',
              f'Deleted folder "{folder_name}". {len(files_in_folder)} file(s) moved to Uncategorized.')
    return jsonify({
        'success': True,
        'message': f'Folder "{folder_name}" deleted. {len(files_in_folder)} file(s) moved to Uncategorized.'
    })


# ====================== FILES ======================
@app.route('/api/files', methods=['GET', 'POST'])
@login_required
def api_files():
    if request.method == 'GET':
        # Optional folder filter
        folder_id = request.args.get('folder_id')
        query = File.query
        if folder_id is not None:
            if folder_id == 'uncategorized':
                query = query.filter(File.folder_id.is_(None))
            else:
                try:
                    fid = int(folder_id)
                    query = query.filter_by(folder_id=fid)
                except ValueError:
                    return jsonify([])
        # All authenticated users see all files
        files = query.order_by(File.uploaded_at.desc()).all()
        return jsonify([f.to_dict() for f in files])

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

    # Validate file type before saving to disk (security)
    if ext not in ALL_ALLOWED_EXTENSIONS:
        return jsonify({'error': f'File type .{ext} is not allowed'}), 400

    unique_name = f"{uuid.uuid4().hex}_{filename}"
    path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
    file.save(path)

    file_type = get_file_type(ext)

    # Handle folder association
    folder_id = None
    raw_folder_id = request.form.get('folder_id')
    if raw_folder_id and raw_folder_id != 'uncategorized':
        try:
            fid = int(raw_folder_id)
            folder = Folder.query.get(fid)
            if folder and (folder.user_id == current_user.id or current_user.role == 'admin'):
                folder_id = fid
        except ValueError:
            pass

    new_file = File(
        filename=unique_name,
        original_filename=filename,
        file_type=file_type,
        file_size=f"{os.path.getsize(path) / (1024 * 1024):.2f} MB",
        file_path=path,
        user_id=current_user.id,
        folder_id=folder_id
    )
    db.session.add(new_file)
    db.session.commit()
    log_audit('UPLOAD', f'Uploaded {filename}')
    return jsonify(new_file.to_dict()), 201


@app.route('/api/files/<int:file_id>', methods=['DELETE'])
@login_required
def api_delete_file(file_id):
    file = File.query.get_or_404(file_id)

    if current_user.role == 'user' and file.user_id != current_user.id:
        return jsonify({'error': 'Can only delete your own files'}), 403

    try:
        if os.path.exists(file.file_path):
            os.remove(file.file_path)
    except Exception as e:
        print(f"Error deleting file: {e}")

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
        return send_file(file.file_path, as_attachment=False, download_name=file.original_filename)
    return jsonify({'error': 'File not found'}), 404


# ====================== AUDIT TRAIL ======================
@app.route('/api/audit-trail')
@login_required
def api_audit_trail():
    date_range = request.args.get('date_range', 'all')
    activity_type = request.args.get('activity_type', 'all')
    user_filter = request.args.get('user', 'all')
    role_filter = request.args.get('role', 'all')

    query = AuditTrail.query

    # Custom date range - use timezone-aware parsing
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if start_date and end_date:
        start = parse_date(start_date)
        end = parse_date(end_date)
        if start and end:
            end = end + timedelta(days=1)
            query = query.filter(AuditTrail.created_at >= start, AuditTrail.created_at < end)
    elif date_range == 'today':
        # Calculate today based on Manila timezone
        manila_now = datetime.now(MANILA_TZ)
        today_start_manila = manila_now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end_manila = today_start_manila + timedelta(days=1)
        # Convert to UTC for database query
        today_start = today_start_manila.astimezone(timezone.utc)
        today_end = today_end_manila.astimezone(timezone.utc)
        query = query.filter(AuditTrail.created_at >= today_start, AuditTrail.created_at < today_end)
    elif date_range == 'week':
        week_ago = now_utc() - timedelta(days=7)
        query = query.filter(AuditTrail.created_at >= week_ago)
    elif date_range == 'month':
        month_ago = now_utc() - timedelta(days=30)
        query = query.filter(AuditTrail.created_at >= month_ago)
    elif date_range == 'year':
        year_ago = now_utc() - timedelta(days=365)
        query = query.filter(AuditTrail.created_at >= year_ago)

    # Activity type filter
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

    # User filter
    if user_filter != 'all':
        query = query.filter(AuditTrail.user_id == int(user_filter))

    # Role filter
    if role_filter != 'all':
        query = query.join(User).filter(User.role == role_filter)

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    pagination = query.order_by(AuditTrail.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'items': [t.to_dict() for t in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
        'per_page': per_page
    })


@app.route('/api/audit-trail/stats')
@login_required
def api_audit_stats():
    today_start = now_utc().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    total = AuditTrail.query.count()
    uploads = AuditTrail.query.filter_by(action='UPLOAD').count()
    downloads = AuditTrail.query.filter_by(action='DOWNLOAD').count()
    today_logins = AuditTrail.query.filter(
        AuditTrail.action == 'LOGIN',
        AuditTrail.created_at >= today_start,
        AuditTrail.created_at < today_end
    ).count()

    all_actions = db.session.query(AuditTrail.action, db.func.count(AuditTrail.id)).group_by(AuditTrail.action).all()
    action_breakdown = {action: count for action, count in all_actions}

    return jsonify({
        'total_activities': total,
        'uploads': uploads,
        'downloads': downloads,
        'today_logins': today_logins,
        'action_breakdown': action_breakdown
    })


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
        if current_user.role not in ['admin', 'user']:
            return jsonify({'error': 'Permission denied'}), 403
        db.session.delete(announcement)
        db.session.commit()
        log_audit('DELETE', f'Deleted announcement: {announcement.title}')
        return jsonify({'success': True, 'message': 'Announcement deleted'})

    if current_user.role not in ['admin', 'user']:
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
    # Security: Restrict dashboard statistics to admin users only.
    # Non-admin users receive 403 Forbidden to prevent data leakage.
    if current_user.role != 'admin':
        return jsonify({'error': 'Permission denied'}), 403

    total_files = File.query.count()
    total_users = User.query.filter_by(status='active').count()
    storage_mb = get_total_storage_mb()
    week_ago = now_utc() - timedelta(days=7)
    recent_activity = AuditTrail.query.filter(
        AuditTrail.created_at >= week_ago
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


@app.route('/api/stats')
@login_required
def api_stats():
    # Security: Restrict dashboard statistics to admin users only.
    # This ensures unauthorized users cannot access statistics via direct API calls.
    if current_user.role != 'admin':
        return jsonify({'error': 'Permission denied'}), 403

    total_files = File.query.count()
    total_users = User.query.filter_by(status='active').count()
    storage_mb = get_total_storage_mb()
    week_ago = now_utc() - timedelta(days=7)
    recent_activity = AuditTrail.query.filter(
        AuditTrail.created_at >= week_ago
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


# ====================== NOTIFICATIONS (PLACEHOLDER) ======================
@app.route('/api/notifications')
@login_required
def api_notifications():
    return jsonify([])


@app.route('/api/notifications/unread-count')
@login_required
def api_notification_count():
    return jsonify({'count': 0})


@app.route('/api/messages')
@login_required
def api_messages():
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

        admin = User(
            first_name='Admin',
            last_name='User',
            email='admin@documanage.com',
            role='admin',
            department='Administration',
            status='active',
            id_number=f"EMP-{datetime.now(timezone.utc).year}-001"
        )
        admin.set_password('admin123')
        db.session.add(admin)

        user = User(
            first_name='User',
            last_name='User',
            email='user@documanage.com',
            role='user',
            department='Operations',
            status='active',
            id_number=f"EMP-{datetime.now(timezone.utc).year}-002"
        )
        user.set_password('user123')
        db.session.add(user)

        db.session.commit()
        print("Default users created!")

    if Announcement.query.count() == 0:
        print("Creating sample announcements...")

        admin_user = User.query.filter_by(email='admin@documanage.com').first()
        user_user = User.query.filter_by(email='user@documanage.com').first()

        announcements = [
            Announcement(
                title='Welcome to OQAADMS v2.0!',
                content='We are excited to announce the launch of OQAADMS v2.0. This new version includes a brand new Home page with announcements, improved search functionality, calendar-based audit reports, and a refreshed user interface. Thank you for choosing OQAADMS for your document management needs.',
                category='announcement',
                author_id=admin_user.id if admin_user else None
            ),
            Announcement(
                title='Weekly Report - System Performance',
                content='This week our system achieved 99.9% uptime. We processed over 1,250 file uploads and 3,400 downloads. Storage usage is at 42% capacity. No critical issues were reported. The new calendar reporting feature has been successfully deployed.',
                category='weekly_report',
                author_id=user_user.id if user_user else None
            ),
            Announcement(
                title='New Feature: Calendar-Based Reports',
                content='We have added a new calendar feature to the Audit Trail page. You can now select specific date ranges (single day, week, or month) to generate detailed activity reports. These reports can be printed or downloaded as PDF files for your records.',
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
                content='Please remember that all documents stored in OQAADMS are subject to our retention policy. Inactive files older than 2 years may be archived. Please review your files and ensure important documents are properly categorized.',
                category='general',
                author_id=user_user.id if user_user else None
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
    print("OQAADMS running at http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)