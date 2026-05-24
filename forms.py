# forms.py - WTForms definitions (alternative organization)
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, EmailField, TextAreaField, FileField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional

class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')

class RegisterForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=100)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=100)])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    user_type = SelectField('User Type', choices=[
        ('', 'Select User Type'),
        ('admin', 'Administrator'),
        ('user', 'User'),

    ], validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    agree_terms = BooleanField('I agree to the Terms of Service', validators=[DataRequired()])

class FileUploadForm(FlaskForm):
    file = FileField('File', validators=[DataRequired()])
    description = TextAreaField('Description')

class ShareFileForm(FlaskForm):
    email = EmailField('Share with', validators=[DataRequired(), Email()])
    permission = SelectField('Permission', choices=[
        ('view', 'Can View'),
        ('edit', 'Can Edit'),
        ('comment', 'Can Comment')
    ])
    message = TextAreaField('Message')