def audit(db, actor, action, subject):
    db.execute('INSERT INTO audit_log (actor, action, subject) VALUES (%s, %s, %s)',
               (actor, action, str(subject)))
