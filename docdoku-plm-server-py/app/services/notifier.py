"""邮件通知——对齐 Payara INotifierLocal.sendBulkIndexationSuccess/Failure。"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

_SMTP_HOST = "smtp"
_SMTP_PORT = 1025
_FROM_ADDR = "noreply@docdokuplm.com"
_SUBJECT_PREFIX = "DocDokuPLM: "

_I18N = {
    "zh": {
        "success_subject": "Bulk 索引成功",
        "success_body": "<HTML><BODY>The bulk request has succeed.</BODY></HTML>",
        "failure_subject": "Bulk 索引失败",
        "failure_body": "<HTML><BODY>The bulk request has failed. Errors: {errors}</BODY></HTML>",
    },
    "en": {
        "success_subject": "Bulk indexing success",
        "success_body": "<HTML><BODY>The bulk request has succeed.</BODY></HTML>",
        "failure_subject": "Bulk indexing failure",
        "failure_body": "<HTML><BODY>The bulk request has failed. Errors: {errors}</BODY></HTML>",
    },
}


def _t(key: str, locale: str, **kwargs) -> str:
    table = _I18N.get(locale, _I18N["en"])
    return table[key].format(**kwargs)


def _send_email(to_email: str, to_name: str, subject: str, body_html: str) -> None:
    msg = MIMEMultipart()
    msg["From"] = _FROM_ADDR
    msg["To"] = to_email
    msg["Subject"] = _SUBJECT_PREFIX + subject
    msg.attach(MIMEText(body_html, "html", "utf-8"))
    try:
        with smtplib.SMTP(_SMTP_HOST, _SMTP_PORT, timeout=10) as server:
            server.sendmail(_FROM_ADDR, [to_email], msg.as_string())
    except Exception:
        logger.warning("Failed to send reindex notification to %s", to_email, exc_info=True)


def send_bulk_indexation_success(account, locale: str = "en") -> None:
    subject = _t("success_subject", locale)
    body = _t("success_body", locale)
    _send_email(account.email, getattr(account, "name", ""), subject, body)


def send_bulk_indexation_failure(account, failure_message: str, locale: str = "en") -> None:
    subject = _t("failure_subject", locale)
    body = _t("failure_body", locale, errors=failure_message[:500])
    _send_email(account.email, getattr(account, "name", ""), subject, body)
