import os
from django.db import connection, transaction
from django.utils import timezone


class FileUploadRepository:
    """Queries the existing Banglarbhumi tables; never creates or migrates them."""

    @staticmethod
    def _table(name):
        schema = os.getenv("DB_SCHEMA", "public")
        # Schema comes from server configuration, never from request data.
        if not schema.replace("_", "").isalnum():
            raise ValueError("Invalid DB_SCHEMA setting.")
        return f'"{schema}"."{name}"'

    @classmethod
    def create_metadata(cls, *, file_name, applnno, idn, file_type, uploaded_by):
        # The public API deliberately does not accept idn. The database requires it,
        # so only a trusted server-side value can enable this tracking insert.
        if not str(idn or "").strip():
            return False, "idn_not_available"
        sql = f"""
            INSERT INTO {cls._table('file_upload')}
                (file_name, applnno, creation_time, idn, file_type, uploaded_by)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(sql, [file_name, applnno, timezone.now(), idn, file_type, uploaded_by])
        return True, None

    @classmethod
    def mrns_for_arn(cls, applnno):
        sql = f"SELECT mrn FROM {cls._table('file_upload')} WHERE applnno = %s AND mrn IS NOT NULL"
        with connection.cursor() as cursor:
            cursor.execute(sql, [applnno])
            return [str(row[0]) for row in cursor.fetchall() if row[0]]

    @classmethod
    def update_mrn(cls, applnno, file_name, mrn):
        # Update only the newest unfinalized tracking row for this document ID.
        # This avoids overwriting an older MRN if the same ID was staged again.
        table = cls._table("file_upload")
        sql = f"""
            WITH target AS (
                SELECT ctid FROM {table}
                WHERE applnno = %s AND file_name = %s AND mrn IS NULL
                ORDER BY creation_time DESC
                LIMIT 1
            )
            UPDATE {table} SET mrn = %s
            WHERE ctid = (SELECT ctid FROM target)
        """
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(sql, [applnno, file_name, mrn])
            return cursor.rowcount

    @classmethod
    def file_names_for_arn(cls, applnno):
        sql = f"SELECT file_name FROM {cls._table('file_upload')} WHERE applnno = %s"
        with connection.cursor() as cursor:
            cursor.execute(sql, [applnno])
            return [str(row[0]) for row in cursor.fetchall() if row[0] is not None]

    @classmethod
    def service_file_list(cls, applnno, service_code):
        names = list(dict.fromkeys(cls.file_names_for_arn(applnno)))
        if not names:
            return []
        table = cls._table("ack_details")
        placeholders = ", ".join(["%s"] * len(names))
        sql = (
            f"SELECT ackdetails_eng FROM {table} "
            f"WHERE code = %s AND slno::text IN ({placeholders})"
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, [service_code, *names])
            return [{"fileName": row[0]} for row in cursor.fetchall() if row[0]]
