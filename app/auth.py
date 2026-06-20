# -*- coding: utf-8 -*-
"""احراز هویت و کنترل دسترسی نقش‌محور (buyer / supplier / admin)."""
import functools

from flask import g, jsonify, redirect, request, session, url_for

from app.models import User


def get_current_user():
    if "_user" in g:
        return g._user
    uid = session.get("user_id")
    user = User.query.get(uid) if uid else None
    g._user = user
    return user


def login_required_page(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not get_current_user():
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def role_required_page(*roles):
    def decorator(view):
        @functools.wraps(view)
        def wrapped(*args, **kwargs):
            user = get_current_user()
            if not user:
                return redirect(url_for("login", next=request.path))
            if user.role not in roles:
                return redirect(url_for("index"))
            return view(*args, **kwargs)

        return wrapped

    return decorator


def role_required_api(*roles):
    def decorator(view):
        @functools.wraps(view)
        def wrapped(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({"error": "برای ادامه ابتدا وارد حساب کاربری شوید"}), 401
            if roles and user.role not in roles:
                return jsonify({"error": "دسترسی شما به این بخش مجاز نیست"}), 403
            return view(*args, **kwargs)

        return wrapped

    return decorator
