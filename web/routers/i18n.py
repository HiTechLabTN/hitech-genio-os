"""Locale catalogue and RTL metadata — Plan v1 §4.6."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from core import i18n

router = APIRouter(prefix="/api", tags=["i18n"])


@router.get("/i18n")
def locales():
    return {
        "ok": True,
        "default": i18n.DEFAULT_LOCALE,
        "locales": i18n.available(),
        "audit": i18n.key_report(),
    }


@router.get("/i18n/{locale}")
def catalogue(locale: str):
    if locale not in i18n.LOCALES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"locale غير معروف: {locale}")
    try:
        return {"ok": True, **i18n.catalogue(locale)}
    except i18n.LocaleError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
