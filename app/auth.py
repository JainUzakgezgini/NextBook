from urllib.parse import urlsplit

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app import db, limiter
from app.forms import ForgotPasswordForm, LoginForm, RegisterForm, ResetPasswordForm
from app.models import User
from app.services.mailer import send_email

bp = Blueprint("auth", __name__)


def safe_next_url(target):
    """Only allow redirects to a page on this site (blocks open-redirect attacks).

    "/books/3" is fine. "https://evil.com", "//evil.com" and "/\\evil.com"
    (which browsers also treat as another site) are rejected.
    """
    if not target or not target.startswith("/") or target.startswith("//") or "\\" in target:
        return None
    parts = urlsplit(target)
    if parts.scheme or parts.netloc:
        return None
    return target


@bp.route("/register", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data.lower())
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Welcome to NextBook. Your shelf is ready.", "success")
        return redirect(url_for("main.dashboard"))
    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute; 30 per hour", methods=["POST"])  # slows down password guessing
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(db.select(User).filter_by(username=form.username.data))
        if user is None or not user.check_password(form.password.data):
            current_app.logger.warning("Failed login for username %r from %s", form.username.data, request.remote_addr)
            flash("Wrong username or password.", "danger")
            return render_template("auth/login.html", form=form), 401
        login_user(user, remember=form.remember.data)
        return redirect(safe_next_url(request.args.get("next")) or url_for("main.dashboard"))
    return render_template("auth/login.html", form=form)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You're logged out.", "info")
    return redirect(url_for("main.index"))


@bp.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("3 per minute; 10 per hour", methods=["POST"])  # stops e-mail spam
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = db.session.scalar(db.select(User).filter_by(email=form.email.data.lower()))
        if user:
            path = url_for("auth.reset_password", token=user.make_reset_token())
            # Build the link from the fixed public address, never from the visitor's request,
            # so a forged "Host" header can't make the e-mail point to an attacker's site.
            base = current_app.config["APP_BASE_URL"] or request.host_url.rstrip("/")
            link = base + path
            minutes = current_app.config["PASSWORD_RESET_MAX_AGE"] // 60
            send_email(
                to=user.email,
                subject="Reset your NextBook password",
                body=(
                    f"Hi {user.username},\n\n"
                    "Someone (hopefully you) asked to reset the password for your NextBook account.\n"
                    f"Your username is: {user.username}\n\n"
                    f"Open this link to choose a new password. It works once, for {minutes} minutes:\n"
                    f"{link}\n\n"
                    "If you didn't ask for this, you can ignore this e-mail. Your password stays the same.\n\n"
                    "NextBook"
                ),
                debug_link=link,
            )
        # Same answer whether or not the address has an account, so nobody can use this
        # page to find out who is registered.
        flash(
            "If an account uses that e-mail address, we've sent it a reset link. "
            "Check your inbox and your spam folder. The link works for 30 minutes.",
            "info",
        )
        return redirect(url_for("auth.login"))
    return render_template("auth/forgot_password.html", form=form)


@bp.route("/reset-password/<token>", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def reset_password(token):
    user = User.from_reset_token(token)
    if user is None:
        flash("This reset link is invalid, has expired or was already used. Ask for a new one below.", "warning")
        return redirect(url_for("auth.forgot_password"))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)  # also signs the account out on every device
        db.session.commit()
        logout_user()
        current_app.logger.info("Password reset completed for user id %s", user.id)
        flash("Your password was changed. Log in with your new password.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/reset_password.html", form=form, username=user.username)
